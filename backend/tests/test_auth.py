def test_register_returns_token(client):
    resp = client.post("/api/auth/register", json={"username": "alice", "password": "secret"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "alice"
    assert body["token"]


def test_register_duplicate_username_rejected(client):
    client.post("/api/auth/register", json={"username": "bob", "password": "secret"})
    resp = client.post("/api/auth/register", json={"username": "bob", "password": "other"})
    assert resp.status_code == 400


def test_register_short_username_rejected(client):
    resp = client.post("/api/auth/register", json={"username": "ab", "password": "secret"})
    assert resp.status_code == 400


def test_login_with_valid_credentials(client):
    client.post("/api/auth/register", json={"username": "carol", "password": "secret"})
    resp = client.post("/api/auth/login", json={"username": "carol", "password": "secret"})
    assert resp.status_code == 200
    assert resp.json()["token"]


def test_login_wrong_password_rejected(client):
    client.post("/api/auth/register", json={"username": "dave", "password": "secret"})
    resp = client.post("/api/auth/login", json={"username": "dave", "password": "wrong"})
    assert resp.status_code == 401


def test_protected_route_requires_token(client):
    resp = client.get("/api/todos")
    assert resp.status_code == 401


def test_protected_route_rejects_bad_token(client):
    resp = client.get("/api/todos", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401
