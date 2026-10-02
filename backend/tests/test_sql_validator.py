import pytest

from app.security.sql_validator import SQLValidationError, SQLValidator

VALID = [
    "SELECT * FROM users;",
    "SELECT COUNT(*) FROM users;",
    "WITH x AS (SELECT id FROM users) SELECT * FROM x",
    "SELECT id FROM a UNION ALL SELECT id FROM b",
    "SELECT u.name, COUNT(o.id) FROM users u JOIN orders o ON o.user_id = u.id GROUP BY u.name",
]

INVALID = [
    "DROP TABLE users;",
    "DELETE FROM users;",
    "UPDATE users SET name='x';",
    "INSERT INTO users VALUES (1, 'a');",
    "ALTER TABLE users ADD COLUMN x int;",
    "TRUNCATE users;",
    "CREATE TABLE t (a int);",
    "GRANT ALL ON users TO bob;",
    "REVOKE ALL ON users FROM bob;",
    "COPY users TO '/tmp/x';",
    "MERGE INTO a USING b ON a.id=b.id WHEN MATCHED THEN DELETE;",
    "CALL do_something();",
    "BEGIN;",
    "SELECT * FROM users; SELECT * FROM orders;",
    "SELECT 1; DROP TABLE users;",
    "WITH d AS (DELETE FROM users RETURNING *) SELECT * FROM d",
    "SELECT * INTO backup FROM users",
    "SELECT * FROM users FOR UPDATE",
    "SELECT pg_sleep(30)",
    "SELECT pg_read_file('/etc/passwd')",
    "",
]


@pytest.mark.parametrize("sql", VALID)
def test_valid_queries_pass(sql):
    assert SQLValidator.validate(sql, max_rows=100).upper().startswith(("SELECT", "WITH"))


@pytest.mark.parametrize("sql", INVALID)
def test_invalid_queries_rejected(sql):
    with pytest.raises(SQLValidationError):
        SQLValidator.validate(sql, max_rows=100)


def test_limit_added_to_unbounded_select():
    assert SQLValidator.validate("SELECT * FROM users", 100).endswith("LIMIT 100")


def test_limit_capped_when_too_large():
    assert SQLValidator.validate("SELECT * FROM users LIMIT 5000", 100).endswith("LIMIT 100")


def test_small_limit_preserved():
    assert SQLValidator.validate("SELECT * FROM users LIMIT 5", 100).endswith("LIMIT 5")


def test_count_aggregate_not_modified():
    assert SQLValidator.validate("SELECT COUNT(*) FROM users;", 100) == "SELECT COUNT(*) FROM users"


def test_group_by_gets_limit():
    out = SQLValidator.validate("SELECT city, COUNT(*) FROM users GROUP BY city", 100)
    assert out.endswith("LIMIT 100")
