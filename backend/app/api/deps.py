from fastapi import Header, HTTPException

from app.database.connection_manager import ActiveConnection, connection_manager


def get_connection(x_connection_id: str | None = Header(default=None)) -> ActiveConnection:
    if not x_connection_id:
        raise HTTPException(status_code=401, detail="Missing X-Connection-ID header.")
    active = connection_manager.get(x_connection_id)
    if not active:
        raise HTTPException(
            status_code=401, detail="Session expired or not connected. Please reconnect to your database."
        )
    return active
