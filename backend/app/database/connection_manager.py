"""Stores active PostgreSQL engines server-side, keyed by connection_id.

The full database URL is never logged and never leaves the server.
"""
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from urllib.parse import urlparse

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url

from app.core.config import get_settings

logger = logging.getLogger("connection_manager")


class ConnectionError_(Exception):
    """Safe, user-facing connection error (never contains credentials)."""


@dataclass
class ActiveConnection:
    engine: Engine
    database_name: str
    host: str
    last_used: float = field(default_factory=time.time)


def normalize_url(db_url: str) -> str:
    """Validate that the URL is PostgreSQL and force the psycopg (v3) driver."""
    db_url = db_url.strip()
    scheme = urlparse(db_url).scheme.lower()
    if scheme not in ("postgresql", "postgres", "postgresql+psycopg"):
        raise ConnectionError_("Only PostgreSQL connection URLs are supported (postgresql://...).")
    try:
        url = make_url(db_url)
    except Exception:
        raise ConnectionError_("The connection URL is not valid.")
    if not url.host or not url.database:
        raise ConnectionError_("The connection URL must include a host and a database name.")
    return url.set(drivername="postgresql+psycopg").render_as_string(hide_password=False)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, ActiveConnection] = {}
        self._lock = threading.Lock()

    def create_connection(self, db_url: str) -> tuple[str, ActiveConnection]:
        settings = get_settings()
        url = make_url(normalize_url(db_url))
        engine = create_engine(
            url,
            pool_size=3,
            max_overflow=2,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 8},
        )
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception as exc:
            engine.dispose()
            logger.error("DB connect failed: %s: %s", type(exc).__name__, (str(exc).splitlines() or [""])[0][:150])
            raise ConnectionError_(
                "Unable to connect to the PostgreSQL database. Please verify the connection details."
            )
        conn_id = uuid.uuid4().hex
        active = ActiveConnection(engine=engine, database_name=url.database, host=url.host)
        with self._lock:
            self._expire_stale(settings.session_ttl_minutes)
            self._connections[conn_id] = active
        return conn_id, active

    def get(self, connection_id: str) -> ActiveConnection | None:
        with self._lock:
            active = self._connections.get(connection_id)
            if active:
                active.last_used = time.time()
            return active

    def get_engine(self, connection_id: str) -> Engine | None:
        active = self.get(connection_id)
        return active.engine if active else None

    def remove_connection(self, connection_id: str) -> bool:
        with self._lock:
            active = self._connections.pop(connection_id, None)
        if active:
            active.engine.dispose()
            return True
        return False

    def _expire_stale(self, ttl_minutes: int) -> None:
        # called with lock held
        cutoff = time.time() - ttl_minutes * 60
        for cid in [c for c, a in self._connections.items() if a.last_used < cutoff]:
            self._connections.pop(cid).engine.dispose()


connection_manager = ConnectionManager()
