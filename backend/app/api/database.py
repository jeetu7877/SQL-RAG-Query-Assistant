import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import get_connection
from app.database.connection_manager import ActiveConnection, ConnectionError_, connection_manager
from app.database.schema_inspector import clear_cache, inspect_schema
from app.models.database import DatabaseConnectRequest, DatabaseConnectResponse, SchemaResponse

logger = logging.getLogger("api.database")
router = APIRouter(prefix="/api/database", tags=["database"])


@router.post("/connect", response_model=DatabaseConnectResponse)
def connect(body: DatabaseConnectRequest):
    try:
        conn_id, active = connection_manager.create_connection(body.database_url)
    except ConnectionError_ as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return DatabaseConnectResponse(
        connection_id=conn_id, database_name=active.database_name, host=active.host
    )


@router.post("/disconnect")
def disconnect(x_connection_id: str | None = Header(default=None)):
    if x_connection_id:
        active = connection_manager.get(x_connection_id)
        if active:
            clear_cache(active.engine)
        connection_manager.remove_connection(x_connection_id)
    return {"status": "disconnected"}


@router.get("/schema", response_model=SchemaResponse)
def schema(refresh: bool = False, active: ActiveConnection = Depends(get_connection)):
    try:
        tables, relationships = inspect_schema(active.engine, use_cache=not refresh)
    except SQLAlchemyError:
        logger.error("Schema inspection failed")
        raise HTTPException(status_code=500, detail="Unable to read the database schema.")
    return SchemaResponse(
        database_name=active.database_name,
        host=active.host,
        tables=tables,
        relationships=relationships,
        table_count=len(tables),
        column_count=sum(len(t.columns) for t in tables),
        relationship_count=len(relationships),
    )
