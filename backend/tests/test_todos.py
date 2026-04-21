def test_todo_crud_flow(auth_client):
    resp = auth_client.post("/api/todos", json={"text": "Buy milk", "priority": "high"})
    assert resp.status_code == 201
    todo = resp.json()
    assert todo["text"] == "Buy milk"
    assert todo["priority"] == "high"
    assert todo["done"] is False
    todo_id = todo["id"]

    resp = auth_client.get("/api/todos")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = auth_client.patch(f"/api/todos/{todo_id}", json={"done": True})
    assert resp.status_code == 200
    assert resp.json()["done"] is True

    resp = auth_client.get("/api/todos?filter=active")
    assert resp.json() == []

    resp = auth_client.delete(f"/api/todos/{todo_id}")
    assert resp.status_code == 204
    assert auth_client.get("/api/todos").json() == []


def test_subtask_lifecycle(auth_client):
    todo_id = auth_client.post("/api/todos", json={"text": "Project"}).json()["id"]

    sub = auth_client.post(f"/api/todos/{todo_id}/subtasks", json={"text": "Step 1"}).json()
    assert sub["done"] is False

    toggled = auth_client.post(f"/api/todos/{todo_id}/subtasks/{sub['id']}/toggle").json()
    assert toggled["done"] is True

    listed = auth_client.get(f"/api/todos/{todo_id}/subtasks").json()
    assert len(listed) == 1


def test_user_cannot_see_other_users_todos(client):
    a = client.post("/api/auth/register", json={"username": "userA", "password": "pw1234"}).json()
    b = client.post("/api/auth/register", json={"username": "userB", "password": "pw5678"}).json()

    client.post(
        "/api/todos",
        json={"text": "A's secret"},
        headers={"Authorization": f"Bearer {a['token']}"},
    )

    resp = client.get("/api/todos", headers={"Authorization": f"Bearer {b['token']}"})
    assert resp.status_code == 200
    assert resp.json() == []


def test_dashboard_returns_zeros_for_new_user(auth_client):
    resp = auth_client.get("/api/dashboard")
    assert resp.status_code == 200
    body = resp.json()
    assert body["todos_active"] == 0
    assert body["todos_done"] == 0
    assert body["habits_total"] == 0


def test_health_endpoint(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
