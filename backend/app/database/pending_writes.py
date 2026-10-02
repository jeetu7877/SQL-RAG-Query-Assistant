"""Holds validated INSERT statements until the user clicks Confirm.

The browser only ever sends back a random single-use token, never SQL, so what runs
is exactly what was previewed. Tokens are bound to one connection and expire quickly.
"""
import secrets
import threading
import time
from dataclasses import dataclass


@dataclass
class PendingWrite:
    connection_id: str
    sql: str
    table: str
    expires_at: float


class PendingWrites:
    def __init__(self) -> None:
        self._items: dict[str, PendingWrite] = {}
        self._lock = threading.Lock()

    def add(self, connection_id: str, sql: str, table: str, ttl_seconds: int) -> str:
        token = secrets.token_urlsafe(24)
        with self._lock:
            now = time.time()
            for t in [t for t, p in self._items.items() if p.expires_at < now]:
                del self._items[t]
            # one pending write per connection: a new preview replaces the old one
            for t in [t for t, p in self._items.items() if p.connection_id == connection_id]:
                del self._items[t]
            self._items[token] = PendingWrite(connection_id, sql, table, now + ttl_seconds)
        return token

    def pop(self, token: str, connection_id: str) -> PendingWrite | None:
        """Single use: returns the item and removes it. None if unknown, expired, or another session's."""
        with self._lock:
            item = self._items.get(token)
            if not item or item.connection_id != connection_id:
                return None
            del self._items[token]
            return item if item.expires_at >= time.time() else None

    def discard(self, token: str, connection_id: str) -> None:
        self.pop(token, connection_id)


pending_writes = PendingWrites()
