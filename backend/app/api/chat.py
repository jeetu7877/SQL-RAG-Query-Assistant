import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.ai import vanna_service
from app.ai.answer_service import build_answer
from app.api.deps import get_connection
from app.core.config import get_settings
from app.database.connection_manager import ActiveConnection
from app.database.query_executor import QueryExecutionError, run_read_only
from app.database.schema_inspector import inspect_schema
from app.models.chat import ChatRequest, ChatResponse
from app.security.sql_validator import SQLValidationError, SQLValidator

logger = logging.getLogger("api.chat")
router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest, active: ActiveConnection = Depends(get_connection)):
    settings = get_settings()

    # 1-2. schema/context for THIS database (cached)
    try:
        tables, _ = inspect_schema(active.engine)
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Unable to read the database schema.")
    if not tables:
        raise HTTPException(status_code=400, detail="No tables were found in the public schema.")

    # 3-5. Vanna + Gemini -> SQL (single LLM call)
    try:
        raw_sql = vanna_service.generate_sql(body.question, tables)
    except vanna_service.AIQuotaError as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    except vanna_service.AIServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    # 6-9. never trust LLM output: validate + cap rows
    try:
        sql = SQLValidator.validate(vanna_service.clean_sql(raw_sql), max_rows=settings.max_result_rows, pretty=True)
    except SQLValidationError:
        raise HTTPException(
            status_code=422,
            detail="The generated SQL failed validation because only read-only queries are allowed. "
            "Try rephrasing your question about the data.",
        )

    # 10. read-only execution with timeout
    try:
        columns, rows, truncated, elapsed_ms = run_read_only(
            active.engine, sql, settings.max_result_rows, settings.query_timeout_seconds
        )
    except QueryExecutionError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return ChatResponse(
        answer=build_answer(body.question, columns, rows, truncated),
        sql=sql,
        columns=columns,
        rows=rows,
        row_count=len(rows),
        truncated=truncated,
        execution_time_ms=elapsed_ms,
    )
