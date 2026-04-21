import os
import sys
import tempfile
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).parent
sys.path.insert(0, str(BACKEND_DIR))

# Use an isolated SQLite file per test session — must be set BEFORE importing app.
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_db.name}"


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from database import Base, engine
    from main import app

    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def auth_client(client):
    """Registered + authenticated client. Adds Bearer token to every request."""
    resp = client.post("/api/auth/register", json={"username": "tester", "password": "pw1234"})
    assert resp.status_code == 200, resp.text
    token = resp.json()["token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client
