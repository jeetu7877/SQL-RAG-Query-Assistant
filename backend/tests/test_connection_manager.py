import pytest

from app.database.connection_manager import ConnectionError_, ConnectionManager, normalize_url


@pytest.mark.parametrize(
    "url",
    [
        "mongodb://u:p@localhost:27017/db",
        "mysql://u:p@localhost:3306/db",
        "sqlite:///test.db",
        "redis://localhost:6379/0",
        "not a url",
        "postgresql://u:p@/db",
    ],
)
def test_rejects_unsupported_or_invalid_urls(url):
    with pytest.raises(ConnectionError_):
        normalize_url(url)


def test_normalizes_to_psycopg_driver():
    assert normalize_url("postgres://u:p@localhost:5432/db").startswith("postgresql+psycopg://")


def test_unreachable_database_gives_safe_error():
    mgr = ConnectionManager()
    with pytest.raises(ConnectionError_) as exc:
        mgr.create_connection("postgresql://user:supersecret@127.0.0.1:1/nodb")
    assert "supersecret" not in str(exc.value)


def test_create_get_remove(db_url):
    mgr = ConnectionManager()
    cid, active = mgr.create_connection(db_url)
    assert mgr.get_engine(cid) is active.engine
    assert mgr.remove_connection(cid) is True
    assert mgr.get_engine(cid) is None
    assert mgr.remove_connection(cid) is False
