"""Task CRUD + comments + validation, acting as DevOps where allowed."""

from fastapi.testclient import TestClient

from .conftest import ANA_ID, owned_task_id


def test_seed_board_has_tasks_in_every_column(client: TestClient, devops: dict):
    tasks = client.get("/api/tasks", headers=devops).json()
    assert len(tasks) == 11
    by_status: dict[str, int] = {}
    for t in tasks:
        by_status[t["status"]] = by_status.get(t["status"], 0) + 1
    assert set(by_status) == {"Backlog", "To Do", "In Progress", "In Review", "Done"}


def test_get_task_detail_includes_comments_and_events(client: TestClient, devops: dict):
    tasks = client.get("/api/tasks", headers=devops).json()
    assert tasks
    detail = client.get(f"/api/tasks/{tasks[0]['id']}", headers=devops).json()
    assert set(detail) >= {"id", "title", "comments", "events", "assigneeId", "priority", "status"}


def test_get_missing_task_is_404_error_shape(client: TestClient, devops: dict):
    r = client.get("/api/tasks/t-ghost", headers=devops)
    assert r.status_code == 404
    assert set(r.json()) == {"error"}


def test_create_task_defaults_and_event(client: TestClient, devops: dict):
    r = client.post("/api/tasks", headers=devops, json={"title": "  New thing  "})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["title"] == "New thing"  # trimmed
    assert body["status"] == "Backlog"
    assert body["priority"] == "Medium"
    assert body["assigneeId"] is None
    assert body["createdBy"] == "u-devops"
    assert body["events"][-1]["type"] == "created"


def test_create_task_validation(client: TestClient, devops: dict):
    assert client.post("/api/tasks", headers=devops, json={"title": "   "}).status_code == 422
    assert client.post("/api/tasks", headers=devops, json={"title": "x" * 121}).status_code == 422
    assert client.post("/api/tasks", headers=devops, json={"title": "ok", "status": "Later"}).status_code == 422
    assert client.post("/api/tasks", headers=devops, json={"title": "ok", "priority": "Urgent"}).status_code == 422
    r = client.post("/api/tasks", headers=devops, json={"title": "ok", "assigneeId": "u-devops"})
    assert r.status_code == 422  # devops id is not a valid assignee
    r = client.post("/api/tasks", headers=devops, json={"title": "ok", "assigneeId": "u-ghost"})
    assert r.status_code == 422


def test_move_own_task_logs_event(client: TestClient, ana: dict):
    task_id = owned_task_id(client, ana, ANA_ID)
    before = client.get(f"/api/tasks/{task_id}", headers=ana).json()
    to = "Done" if before["status"] != "Done" else "Backlog"
    r = client.patch(f"/api/tasks/{task_id}", headers=ana, json={"status": to})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == to
    assert body["updatedAt"] >= before["updatedAt"]
    assert body["events"][-1]["type"] == "moved"


def test_edit_title_and_priority(client: TestClient, ana: dict):
    task_id = owned_task_id(client, ana, ANA_ID)
    r = client.patch(f"/api/tasks/{task_id}", headers=ana, json={"title": "Renamed", "priority": "Low"})
    assert r.status_code == 200
    assert r.json()["title"] == "Renamed"
    assert r.json()["priority"] == "Low"


def test_update_validation(client: TestClient, ana: dict):
    task_id = owned_task_id(client, ana, ANA_ID)
    assert client.patch(f"/api/tasks/{task_id}", headers=ana, json={"title": ""}).status_code == 422
    assert client.patch(f"/api/tasks/{task_id}", headers=ana, json={"status": "Later"}).status_code == 422
    assert client.patch(f"/api/tasks/{task_id}", headers=ana, json={"priority": "Urgent"}).status_code == 422


def test_add_comment_bumps_updated_at(client: TestClient, ana: dict):
    task_id = owned_task_id(client, ana, ANA_ID)
    before = client.get(f"/api/tasks/{task_id}", headers=ana).json()
    r = client.post(f"/api/tasks/{task_id}/comments", headers=ana, json={"body": "Status note"})
    assert r.status_code == 201, r.text
    assert r.json()["body"] == "Status note"
    after = client.get(f"/api/tasks/{task_id}", headers=ana).json()
    assert len(after["comments"]) == len(before["comments"]) + 1
    assert after["updatedAt"] >= before["updatedAt"]
    assert after["events"][-1]["type"] == "commented"


def test_comment_validation(client: TestClient, ana: dict):
    task_id = owned_task_id(client, ana, ANA_ID)
    assert client.post(f"/api/tasks/{task_id}/comments", headers=ana, json={"body": "  "}).status_code == 422
    assert client.post(f"/api/tasks/{task_id}/comments", headers=ana, json={"body": "x" * 2001}).status_code == 422


def test_devops_deletes_task_then_404(client: TestClient, devops: dict):
    created = client.post("/api/tasks", headers=devops, json={"title": "temp"}).json()
    assert client.delete(f"/api/tasks/{created['id']}", headers=devops).status_code == 204
    assert client.get(f"/api/tasks/{created['id']}", headers=devops).status_code == 404
