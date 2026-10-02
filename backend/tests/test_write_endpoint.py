import psycopg
import pytest

from app.api import write as write_api
from app.core.config import get_settings
from app.database import pending_writes as pw

NEW_CUSTOMER = "INSERT INTO customers (name, email, city) VALUES ('Wtest One', 'wtest1@example.com', 'Delhi')"


def _admin(db_url):
    return psycopg.connect(db_url, autocommit=True)


def _count(db_url, table, where="true"):
    with _admin(db_url) as c:
        return c.execute(f"SELECT count(*) FROM {table} WHERE {where}").fetchone()[0]


@pytest.fixture()
def writes_on(monkeypatch):
    monkeypatch.setattr(get_settings(), "allow_writes", True)


@pytest.fixture(autouse=True)
def cleanup(request):
    yield
    if "db_url" in request.fixturenames:
        url = request.getfixturevalue("db_url")
        with _admin(url) as c:
            c.execute("DELETE FROM customers WHERE email LIKE 'wtest%'")
            c.execute("DELETE FROM products WHERE name LIKE 'wtest%' OR name = 'x'")


@pytest.fixture()
def session(client, db_url):
    r = client.post("/api/database/connect", json={"database_url": db_url})
    h = {"X-Connection-ID": r.json()["connection_id"]}
    yield h
    client.post("/api/database/disconnect", headers=h)


def _gen(monkeypatch, sql):
    monkeypatch.setattr(write_api.vanna_service, "generate_insert", lambda q, t: sql)


def test_write_mode_off_by_default(client, session):
    assert get_settings().allow_writes is False
    assert client.get("/api/health").json()["writes_enabled"] is False
    r = client.post("/api/write/preview", json={"question": "add a customer"}, headers=session)
    assert r.status_code == 403


def test_preview_then_confirm_inserts_exactly_once(client, db_url, session, writes_on, monkeypatch):
    _gen(monkeypatch, NEW_CUSTOMER + ";")
    before = _count(db_url, "customers")

    p = client.post("/api/write/preview", json={"question": "add Wtest One"}, headers=session)
    assert p.status_code == 200, p.text
    body = p.json()
    assert body["table"] == "customers" and body["row_count"] == 1 and "Wtest One" in body["sql"]
    assert _count(db_url, "customers") == before  # preview alone changes nothing

    c = client.post("/api/write/confirm", json={"token": body["token"]}, headers=session)
    assert c.status_code == 200, c.text
    assert c.json()["inserted_rows"] == 1
    assert _count(db_url, "customers") == before + 1

    again = client.post("/api/write/confirm", json={"token": body["token"]}, headers=session)
    assert again.status_code == 410  # single use
    assert _count(db_url, "customers") == before + 1


def test_confirm_never_accepts_sql_from_client(client, session, writes_on):
    r = client.post("/api/write/confirm", json={"token": "DELETE FROM customers;--padding"}, headers=session)
    assert r.status_code == 410


def test_token_is_bound_to_its_own_session(client, db_url, session, writes_on, monkeypatch):
    _gen(monkeypatch, NEW_CUSTOMER)
    token = client.post("/api/write/preview", json={"question": "add"}, headers=session).json()["token"]
    other = client.post("/api/database/connect", json={"database_url": db_url}).json()["connection_id"]
    r = client.post("/api/write/confirm", json={"token": token}, headers={"X-Connection-ID": other})
    assert r.status_code == 410
    client.post("/api/database/disconnect", headers={"X-Connection-ID": other})


def test_expired_token(client, session, writes_on, monkeypatch):
    _gen(monkeypatch, NEW_CUSTOMER)
    monkeypatch.setattr(get_settings(), "write_confirm_ttl_seconds", -1)
    token = client.post("/api/write/preview", json={"question": "add"}, headers=session).json()["token"]
    assert client.post("/api/write/confirm", json={"token": token}, headers=session).status_code == 410


def test_cancel_discards(client, session, writes_on, monkeypatch):
    _gen(monkeypatch, NEW_CUSTOMER)
    token = client.post("/api/write/preview", json={"question": "add"}, headers=session).json()["token"]
    client.post("/api/write/cancel", json={"token": token}, headers=session)
    assert client.post("/api/write/confirm", json={"token": token}, headers=session).status_code == 410


@pytest.mark.parametrize("bad", ["DELETE FROM customers", "UPDATE customers SET name='x'",
                                 "DROP TABLE customers", "SELECT * FROM customers"])
def test_non_insert_from_llm_is_rejected_and_data_untouched(client, db_url, session, writes_on, monkeypatch, bad):
    _gen(monkeypatch, bad)
    before = _count(db_url, "customers")
    r = client.post("/api/write/preview", json={"question": "do something bad"}, headers=session)
    assert r.status_code == 422
    assert _count(db_url, "customers") == before


def test_cannot_insert_reason_is_shown(client, session, writes_on, monkeypatch):
    _gen(monkeypatch, "CANNOT_INSERT: email is required")
    r = client.post("/api/write/preview", json={"question": "add a customer"}, headers=session)
    assert r.status_code == 422 and "email is required" in r.json()["detail"]


def test_constraint_violation_saves_nothing(client, db_url, session, writes_on, monkeypatch):
    # email is UNIQUE: inserting the same one twice in a single statement must fail as a whole
    _gen(monkeypatch, "INSERT INTO customers (name,email) VALUES ('Wtest A','wtest2@example.com'),('Wtest B','wtest2@example.com')")
    token = client.post("/api/write/preview", json={"question": "add"}, headers=session).json()["token"]
    r = client.post("/api/write/confirm", json={"token": token}, headers=session)
    assert r.status_code == 400 and "constraint" in r.json()["detail"].lower()
    assert _count(db_url, "customers", "email LIKE 'wtest%'") == 0


def test_too_many_rows_rolled_back(client, db_url, session, writes_on, monkeypatch):
    _gen(monkeypatch, "INSERT INTO products (name, category, price) SELECT 'wtest', 'y', 1 FROM generate_series(1, 200)")
    before = _count(db_url, "products")
    token = client.post("/api/write/preview", json={"question": "add many"}, headers=session).json()["token"]
    r = client.post("/api/write/confirm", json={"token": token}, headers=session)
    assert r.status_code == 400 and "Nothing was saved" in r.json()["detail"]
    assert _count(db_url, "products") == before


def test_read_only_database_user_gets_clear_permission_error(client, db_url, writes_on, monkeypatch):
    with _admin(db_url) as c:
        try:
            c.execute("DROP OWNED BY ro_test")
            c.execute("DROP ROLE IF EXISTS ro_test")
        except Exception:
            pass
        try:
            c.execute("CREATE ROLE ro_test LOGIN PASSWORD 'rotest'")
        except Exception:
            pytest.skip("cannot create a role with this database user")
        c.execute("GRANT USAGE ON SCHEMA public TO ro_test")
        c.execute("GRANT SELECT ON ALL TABLES IN SCHEMA public TO ro_test")
    try:
        ro_url = db_url.replace("postgres:password123", "ro_test:rotest")
        cid = client.post("/api/database/connect", json={"database_url": ro_url}).json()["connection_id"]
        h = {"X-Connection-ID": cid}
        _gen(monkeypatch, NEW_CUSTOMER)
        token = client.post("/api/write/preview", json={"question": "add"}, headers=h).json()["token"]
        r = client.post("/api/write/confirm", json={"token": token}, headers=h)
        assert r.status_code == 400 and "permission" in r.json()["detail"].lower()
        client.post("/api/database/disconnect", headers=h)
    finally:
        with _admin(db_url) as c:
            c.execute("DROP OWNED BY ro_test")
            c.execute("DROP ROLE ro_test")


def test_chat_endpoint_still_read_only_with_writes_enabled(client, session, writes_on, monkeypatch):
    from app.api import chat as chat_api
    monkeypatch.setattr(chat_api.vanna_service, "generate_sql", lambda q, t: NEW_CUSTOMER)
    r = client.post("/api/chat", json={"question": "add a customer"}, headers=session)
    assert r.status_code == 422  # the normal chat path never allows INSERT
