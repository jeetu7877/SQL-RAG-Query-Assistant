import pytest

from app.security.sql_validator import SQLValidationError, validate_insert

TABLES = {"customers", "orders", "products"}

VALID = [
    "INSERT INTO customers (name, email) VALUES ('A', 'a@x.com')",
    "INSERT INTO customers (name, email) VALUES ('A', 'a@x.com'), ('B', 'b@x.com');",
    "INSERT INTO public.customers (name, email) VALUES ('A', 'a@x.com') ON CONFLICT DO NOTHING",
    "INSERT INTO Customers (name, email) VALUES ('A', 'a@x.com')",
    "INSERT INTO products (name, category, price) SELECT 'x', 'y', 1",
]

INVALID = [
    "UPDATE customers SET name = 'x'",
    "DELETE FROM customers",
    "DROP TABLE customers",
    "TRUNCATE customers",
    "SELECT * FROM customers",
    "INSERT INTO customers (name) VALUES ('a'); DROP TABLE customers",
    "INSERT INTO customers (name) VALUES ('a'); INSERT INTO customers (name) VALUES ('b')",
    "INSERT INTO customers (name) VALUES ('a') RETURNING id",
    "INSERT INTO customers (email) VALUES ('a') ON CONFLICT (email) DO UPDATE SET name = 'z'",
    "INSERT INTO other.customers (name) VALUES ('a')",
    "INSERT INTO pg_catalog.pg_class (relname) VALUES ('a')",
    "INSERT INTO secrets (v) VALUES ('a')",
    "WITH d AS (DELETE FROM customers RETURNING *) INSERT INTO products (name, category, price) SELECT 'a','b',1 FROM d",
    "INSERT INTO customers (name) VALUES (pg_sleep(10)::text)",
    "INSERT INTO customers (name) SELECT pg_read_file('/etc/passwd')",
    "COPY customers FROM '/tmp/x'",
    "",
]


@pytest.mark.parametrize("sql", VALID)
def test_valid_inserts_pass(sql):
    check = validate_insert(sql, TABLES, max_rows=50)
    assert check.sql.upper().startswith("INSERT INTO")


@pytest.mark.parametrize("sql", INVALID)
def test_everything_else_rejected(sql):
    with pytest.raises(SQLValidationError):
        validate_insert(sql, TABLES, max_rows=50)


def test_row_count_and_limit():
    two = "INSERT INTO customers (name) VALUES ('a'), ('b')"
    assert validate_insert(two, TABLES, 50).row_count == 2
    with pytest.raises(SQLValidationError):
        validate_insert(two, TABLES, 1)
