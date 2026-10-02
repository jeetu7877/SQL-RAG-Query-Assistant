import os

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def db_url():
    """Set TEST_DATABASE_URL (e.g. the docker-compose sample DB) to run DB-backed tests."""
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL not set")
    return url


@pytest.fixture()
def client():
    return TestClient(app)
