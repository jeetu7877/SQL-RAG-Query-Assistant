"""Verifies the Vanna wiring offline: no Gemini call, no embedding-model download."""
import hashlib

import pytest

from app.ai import vanna_service
from app.core.config import get_settings
from app.models.database import ColumnSchema, ForeignKeySchema, TableSchema


class FakeEmbedding:
    def __init__(self, *a, **k):
        pass

    @staticmethod
    def name():
        return "fake"

    def __call__(self, input):
        out = []
        for text in input:
            v = [0.0] * 64
            for w in text.lower().replace('"', " ").replace("(", " ").split():
                v[int(hashlib.md5(w.encode()).hexdigest(), 16) % 64] += 1.0
            out.append(v)
        return out


def _tables(prefix):
    return [
        TableSchema(name=f"{prefix}_customers", primary_keys=["id"],
                    columns=[ColumnSchema(name="id", type="INTEGER", nullable=False, primary_key=True)]),
        TableSchema(name=f"{prefix}_orders", primary_keys=["id"],
                    columns=[ColumnSchema(name="id", type="INTEGER", nullable=False, primary_key=True),
                             ColumnSchema(name="customer_id", type="INTEGER", nullable=False, foreign_key=True)],
                    foreign_keys=[ForeignKeySchema(columns=["customer_id"], referred_table=f"{prefix}_customers",
                                                   referred_columns=["id"])]),
    ]


@pytest.fixture()
def vanna_env(tmp_path, monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "vanna_data_dir", str(tmp_path))
    monkeypatch.setattr(s, "google_api_key", "fake-key")
    monkeypatch.setattr(vanna_service, "_embedding_function", FakeEmbedding())
    monkeypatch.setattr(vanna_service, "_instances", {})
    return tmp_path


def test_generates_sql_with_only_schema_in_prompt(vanna_env, monkeypatch):
    seen = {}

    def fake_submit(self, prompt, **kw):
        seen["prompt"] = "\n".join(prompt)
        return "```sql\nSELECT COUNT(*) FROM a_customers;\n```"

    monkeypatch.setattr(vanna_service.PostgresVanna, "submit_prompt", fake_submit)
    sql = vanna_service.generate_sql("How many customers?", _tables("a"))
    assert "COUNT(*)" in sql
    assert 'CREATE TABLE "a_customers"' in seen["prompt"] and "PostgreSQL" in seen["prompt"]
    assert "postgresql://" not in seen["prompt"] and "password" not in seen["prompt"].lower()


def test_each_schema_gets_its_own_isolated_store(vanna_env):
    va = vanna_service.get_vanna(_tables("a"))
    vb = vanna_service.get_vanna(_tables("b"))
    assert va is not vb
    docs_a = " ".join(va.ddl_collection.get()["documents"])
    docs_b = " ".join(vb.ddl_collection.get()["documents"])
    assert "a_orders" in docs_a and "b_orders" not in docs_a
    assert "b_orders" in docs_b and "a_orders" not in docs_b
    assert vanna_service.get_vanna(_tables("a")) is va  # cached per fingerprint


def test_missing_api_key_gives_safe_error(vanna_env, monkeypatch):
    monkeypatch.setattr(get_settings(), "google_api_key", "")
    with pytest.raises(vanna_service.AIServiceError):
        vanna_service.generate_sql("q", _tables("c"))


def test_quota_error_mapped(vanna_env, monkeypatch):
    from google.genai import errors

    def boom(self, prompt, **kw):
        raise errors.APIError(429, {"error": {"message": "quota", "status": "RESOURCE_EXHAUSTED"}})

    monkeypatch.setattr(vanna_service.PostgresVanna, "submit_prompt", boom)
    with pytest.raises(vanna_service.AIQuotaError):
        vanna_service.generate_sql("q", _tables("d"))
