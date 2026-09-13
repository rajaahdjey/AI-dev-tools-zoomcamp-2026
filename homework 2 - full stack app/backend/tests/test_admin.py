"""Admin: demo reset reseeds tasks and clears sessions."""

from fastapi.testclient import TestClient

from .conftest import DEVOPS_ID, login



def test_devops_reset_restoreseed_and_revokes_token(client: TestClient, devops: dict):
    created = client.post("/api/tasks", headers=devops, json={"title": "temp"}).json()
    assert client.post("/api/admin/reset", headers=devops).status_code == 204
    fresh = {"Authorization": f"Bearer {login(client, DEVOPS_ID)}"}
    tasks = client.get("/api/tasks", headers=fresh).json()
    assert len(tasks) == 11
    assert created["id"] not in {t["id"] for t in tasks}


def test_developer_cannot_reset(client: TestClient, ana: dict):
    assert client.post("/api/admin/reset", headers=ana).status_code == 403


def test_reset_needs_auth(client: TestClient):
    assert client.post("/api/admin/reset").status_code == 401
