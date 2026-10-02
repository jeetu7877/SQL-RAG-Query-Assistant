import pytest

from app.api import chat as chat_api
from app.database.connection_manager import connection_manager
from app.models.database import ColumnSchema, TableSchema


def _connect(client, db_url):
    r = client.post("/api/database/connect", json={"database_url": db_url})
    assert r.status_code == 200, r.text
    return r.json()


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_chat_requires_connection_header(client):
    r = client.post("/api/chat", json={"question": "How many customers are there?"})
    assert r.status_code == 401


def test_connect_rejects_non_postgres(client):
    r = client.post("/api/database/connect", json={"database_url": "mongodb://u:p@h:27017/db"})
    assert r.status_code == 400
    assert "PostgreSQL" in r.json()["detail"]


def test_connect_response_has_no_password(client, db_url):
    body = _connect(client, db_url)
    assert body["status"] == "connected" and body["database_type"] == "postgresql"
    assert "password" not in str(body).lower() and "password123" not in str(body)
    client.post("/api/database/disconnect", headers={"X-Connection-ID": body["connection_id"]})


def test_schema_endpoint(client, db_url):
    info = _connect(client, db_url)
    h = {"X-Connection-ID": info["connection_id"]}
    data = client.get("/api/database/schema", headers=h).json()
    assert data["table_count"] >= 4 and data["relationship_count"] >= 4
    client.post("/api/database/disconnect", headers=h)
    assert client.get("/api/database/schema", headers=h).status_code == 401


def test_chat_happy_path_with_mocked_llm(client, db_url, monkeypatch):
    monkeypatch.setattr(
        chat_api.vanna_service, "generate_sql",
        lambda q, t: "SELECT COUNT(*) AS customer_count FROM customers;",
    )
    info = _connect(client, db_url)
    h = {"X-Connection-ID": info["connection_id"]}
    r = client.post("/api/chat", json={"question": "How many customers are there?"}, headers=h)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["rows"] == [[60]] and d["columns"] == ["customer_count"]
    assert d["answer"] == "There are 60 customers."
    assert d["row_count"] == 1 and d["execution_time_ms"] >= 0
    client.post("/api/database/disconnect", headers=h)


def test_chat_limits_rows(client, db_url, monkeypatch):
    monkeypatch.setattr(chat_api.vanna_service, "generate_sql", lambda q, t: "SELECT * FROM order_items")
    info = _connect(client, db_url)
    h = {"X-Connection-ID": info["connection_id"]}
    d = client.post("/api/chat", json={"question": "show all order items"}, headers=h).json()
    assert d["row_count"] == 100 and "LIMIT 100" in d["sql"]
    client.post("/api/database/disconnect", headers=h)


@pytest.mark.parametrize(
    "bad_sql",
    ["DROP TABLE customers", "DELETE FROM customers", "SELECT 1; DROP TABLE customers",
     "UPDATE customers SET name='x'"],
)
def test_chat_rejects_write_sql_from_llm(client, db_url, monkeypatch, bad_sql):
    monkeypatch.setattr(chat_api.vanna_service, "generate_sql", lambda q, t: bad_sql)
    info = _connect(client, db_url)
    h = {"X-Connection-ID": info["connection_id"]}
    r = client.post("/api/chat", json={"question": "please destroy everything"}, headers=h)
    assert r.status_code == 422
    assert "read-only" in r.json()["detail"]
    ok = client.get("/api/database/schema", headers=h).json()
    assert "customers" in [t["name"] for t in ok["tables"]]
    client.post("/api/database/disconnect", headers=h)


def test_quota_error_message(client, monkeypatch):
    from app.ai.vanna_service import AIQuotaError
    from app.database.connection_manager import ActiveConnection

    def boom(q, t):
        raise AIQuotaError("AI service quota has been exceeded. Please try again later.")

    t = TableSchema(name="x", columns=[ColumnSchema(name="id", type="INTEGER", nullable=False)])
    monkeypatch.setattr(chat_api, "inspect_schema", lambda e: ([t], []))
    monkeypatch.setattr(chat_api.vanna_service, "generate_sql", boom)
    monkeypatch.setattr(
        "app.api.deps.connection_manager.get",
        lambda cid: ActiveConnection(engine=None, database_name="d", host="h"),
    )
    r = client.post("/api/chat", json={"question": "anything"}, headers={"X-Connection-ID": "abc"})
    assert r.status_code == 429 and "quota" in r.json()["detail"]
