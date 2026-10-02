"""Defense in depth: even if validation were bypassed, Postgres blocks writes."""
import pytest

from app.database.connection_manager import ConnectionManager
from app.database.query_executor import QueryExecutionError, run_read_only


@pytest.fixture()
def engine(db_url):
    mgr = ConnectionManager()
    cid, active = mgr.create_connection(db_url)
    yield active.engine
    mgr.remove_connection(cid)


def test_select_works_and_truncates(engine):
    cols, rows, truncated, ms = run_read_only(engine, "SELECT id FROM orders ORDER BY id", 10, 5)
    assert cols == ["id"] and len(rows) == 10 and truncated and ms >= 0


@pytest.mark.parametrize(
    "sql",
    ["DELETE FROM customers", "DROP TABLE customers", "UPDATE products SET price = 0",
     "INSERT INTO products(name,category,price) VALUES ('x','y',1)"],
)
def test_write_statements_blocked_by_database(engine, sql):
    with pytest.raises(QueryExecutionError):
        run_read_only(engine, sql, 10, 5)
    _, rows, _, _ = run_read_only(engine, "SELECT COUNT(*) FROM customers", 10, 5)
    assert rows[0][0] == 60


def test_statement_timeout(engine):
    with pytest.raises(QueryExecutionError):
        run_read_only(engine, "SELECT COUNT(*) FROM generate_series(1,10000000000)", 10, 1)


def test_percent_and_colon_literals_safe(engine):
    _, rows, _, _ = run_read_only(engine, "SELECT 'a%b' LIKE '%%' AS x, '12:30'::text AS t", 10, 5)
    assert rows[0] == [True, "12:30"]
