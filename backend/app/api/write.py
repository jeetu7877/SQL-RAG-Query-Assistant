"""Write mode: INSERT only, behind a server switch, with preview -> explicit confirm."""
import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.ai import vanna_service
from app.api.deps import get_connection
from app.core.config import get_settings
from app.database.connection_manager import ActiveConnection
from app.database.pending_writes import pending_writes
from app.database.query_executor import WriteExecutionError, run_insert
from app.database.schema_inspector import clear_cache, inspect_schema
from app.models.write import (
    WriteConfirmRequest,
    WriteConfirmResponse,
    WritePreviewRequest,
    WritePreviewResponse,
)
from app.security.sql_validator import SQLValidationError, validate_insert

logger = logging.getLogger("api.write")
router = APIRouter(prefix="/api/write", tags=["write"])


def require_writes_enabled() -> None:
    if not get_settings().allow_writes:
        raise HTTPException(
            status_code=403,
            detail="Write mode is disabled on this server. The operator must set ALLOW_WRITES=true.",
        )


@router.post("/preview", response_model=WritePreviewResponse, dependencies=[Depends(require_writes_enabled)])
def preview(
    body: WritePreviewRequest,
    active: ActiveConnection = Depends(get_connection),
    x_connection_id: str = Header(),
):
    s = get_settings()
    try:
        tables, _ = inspect_schema(active.engine)
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Unable to read the database schema.")
    if not tables:
        raise HTTPException(status_code=400, detail="No tables were found in the public schema.")

    try:
        raw = vanna_service.generate_insert(body.question, tables)
    except vanna_service.AIQuotaError as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    except vanna_service.AIServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    cleaned = vanna_service.clean_sql(raw)
    if cleaned.upper().startswith("CANNOT_INSERT"):
        reason = cleaned.split(":", 1)[-1].strip()[:200] or "More details are needed."
        raise HTTPException(status_code=422, detail=f"I can't build that insert: {reason}")

    try:
        check = validate_insert(cleaned, {t.name for t in tables}, s.max_write_rows)
    except SQLValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"The generated statement was rejected: {exc} Write mode only allows plain INSERT statements.",
        )

    token = pending_writes.add(x_connection_id, check.sql, check.table, s.write_confirm_ttl_seconds)
    return WritePreviewResponse(
        token=token, sql=check.sql, table=check.table,
        row_count=check.row_count, expires_in_seconds=s.write_confirm_ttl_seconds,
    )


@router.post("/confirm", response_model=WriteConfirmResponse, dependencies=[Depends(require_writes_enabled)])
def confirm(
    body: WriteConfirmRequest,
    active: ActiveConnection = Depends(get_connection),
    x_connection_id: str = Header(),
):
    s = get_settings()
    pending = pending_writes.pop(body.token, x_connection_id)
    if not pending:
        raise HTTPException(status_code=410, detail="This insert expired or was already used. Please ask again.")
    try:
        inserted, elapsed = run_insert(active.engine, pending.sql, s.max_write_rows, s.query_timeout_seconds)
    except WriteExecutionError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    clear_cache(active.engine)  # row estimates changed
    logger.info("INSERT committed table=%s rows=%s", pending.table, inserted)  # never log values
    return WriteConfirmResponse(
        inserted_rows=inserted, table=pending.table, execution_time_ms=elapsed,
        message=f"Inserted {inserted} row{'s' if inserted != 1 else ''} into {pending.table}.",
    )


@router.post("/cancel")
def cancel(body: WriteConfirmRequest, x_connection_id: str = Header()):
    pending_writes.discard(body.token, x_connection_id)
    return {"status": "cancelled"}
