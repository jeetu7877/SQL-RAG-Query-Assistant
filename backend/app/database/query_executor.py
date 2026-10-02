"""Executes already-validated SQL in a read-only, time-limited transaction."""
import time
from typing import Any

from sqlalchemy.engine import Engine


class QueryExecutionError(Exception):
    pass


def _jsonable(v: Any) -> Any:
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, (bytes, bytearray, memoryview)):
        return "<binary>"
    return str(v)  # Decimal, date, datetime, UUID, JSON, arrays ...


def run_read_only(engine: Engine, sql: str, max_rows: int, timeout_seconds: int):
    """Returns (columns, rows, truncated, elapsed_ms).

    Uses the raw DBAPI cursor so '%' and ':' inside the SQL are never treated
    as bind-parameter markers.
    """
    raw = engine.raw_connection()
    try:
        raw.read_only = True  # BEGIN READ ONLY: Postgres itself blocks writes
        cur = raw.cursor()
        cur.execute(f"SET LOCAL statement_timeout = {int(timeout_seconds) * 1000}")
        start = time.perf_counter()
        try:
            cur.execute(sql)
            columns = [d.name for d in (cur.description or [])]
            fetched = cur.fetchmany(max_rows + 1)
        except Exception:
            raise QueryExecutionError("The query could not be executed. Please try rephrasing your question.")
        elapsed = (time.perf_counter() - start) * 1000
        truncated = len(fetched) > max_rows
        rows = [[_jsonable(v) for v in r] for r in fetched[:max_rows]]
        return columns, rows, truncated, round(elapsed, 2)
    finally:
        try:
            raw.rollback()
            raw.read_only = False
        except Exception:
            pass
        raw.close()  # returns connection to the pool
