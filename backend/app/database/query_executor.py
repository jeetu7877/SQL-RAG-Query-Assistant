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


class WriteExecutionError(Exception):
    """Safe, user-facing write error."""


def run_insert(engine: Engine, sql: str, max_rows: int, timeout_seconds: int) -> tuple[int, float]:
    """Run ONE validated INSERT in a single transaction. Returns (rows_inserted, elapsed_ms).

    Rolls back (nothing is saved) if it fails or touches more than max_rows rows.
    """
    import psycopg.errors as pge

    raw = engine.raw_connection()
    try:
        raw.read_only = False
        cur = raw.cursor()
        cur.execute(f"SET LOCAL statement_timeout = {int(timeout_seconds) * 1000}")
        start = time.perf_counter()
        try:
            cur.execute(sql)
            inserted = cur.rowcount if cur.rowcount is not None else 0
            if inserted > max_rows:
                raw.rollback()
                raise WriteExecutionError(
                    f"The insert would add {inserted} rows, above the limit of {max_rows}. Nothing was saved."
                )
            raw.commit()
        except WriteExecutionError:
            raise
        except pge.InsufficientPrivilege:
            raw.rollback()
            raise WriteExecutionError(
                "This database user does not have INSERT permission. Connect with a user that is allowed to write."
            )
        except pge.IntegrityError as exc:
            raw.rollback()
            name = getattr(getattr(exc, "diag", None), "constraint_name", None)
            raise WriteExecutionError(
                "The insert was rejected by a database constraint"
                + (f" ({name})" if name else "")
                + " such as NOT NULL, UNIQUE or FOREIGN KEY. Nothing was saved."
            )
        except Exception:
            raw.rollback()
            raise WriteExecutionError("The insert could not be executed. Nothing was saved.")
        return inserted, round((time.perf_counter() - start) * 1000, 2)
    finally:
        try:
            raw.rollback()
        except Exception:
            pass
        raw.close()
