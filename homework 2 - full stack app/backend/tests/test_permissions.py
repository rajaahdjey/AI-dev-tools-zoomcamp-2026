"""Permission matrix: DevOps vs developer vs unassigned (spec §3)."""

from fastapi.testclient import TestClient

from .conftest import ANA_ID, BEN_ID, owned_task_id


def test_developer_cannot_create(client: TestClient, ana: dict):
    r = client.post("/api/tasks", headers=ana, json={"title": "sneaky"})
    assert r.status_code == 403
    assert set(r.json()) == {"error"}

def test_developer_cannot_touch_others_task(client: TestClient, ana: dict, ben: dict):
    task_id = owned_task_id(client, ben, BEN_ID)
    before = client.get(f"/api/tasks/{task_id}", headers=ben).json()
    assert client.patch(f"/api/tasks/{task_id}", headers=ana, json={"status": "Done"}).status_code == 403
    assert client.patch(f"/api/tasks/{task_id}", headers=ana, json={"title": "hijack"}).status_code == 403
    r = client.post(f"/api/tasks/{task_id}/comments", headers=ana, json={"body": "hi"})
    assert r.status_code == 403
    after = client.get(f"/api/tasks/{task_id}", headers=ben).json()
    assert after["status"] == before["status"]
    assert after["title"] == before["title"]
    assert len(after["comments"]) == len(before["comments"])


def test_developer_cannot_reassign_even_own_task(client: TestClient, ana: dict):
    task_id = owned_task_id(client, ana, ANA_ID)
    r = client.patch(f"/api/tasks/{task_id}", headers=ana, json={"assigneeId": BEN_ID})
    assert r.status_code == 403


def test_developer_unassigned_task_is_read_only(client: TestClient, ana: dict):
    tasks = client.get("/api/tasks", headers=ana).json()
    unassigned = [t for t in tasks if t["assigneeId"] is None]
    assert unassigned, "seed must include unassigned tasks"
    task_id = unassigned[0]["id"]
    assert client.patch(f"/api/tasks/{task_id}", headers=ana, json={"status": "Done"}).status_code == 403
    r = client.post(f"/api/tasks/{task_id}/comments", headers=ana, json={"body": "hi"})
    assert r.status_code == 403


def test_devops_can_move_edit_comment_any_task(client: TestClient, devops: dict, ana: dict):
    task_id = owned_task_id(client, ana, ANA_ID)
    assert client.patch(f"/api/tasks/{task_id}", headers=devops, json={"title": "triage edit"}).status_code == 200
    r = client.post(f"/api/tasks/{task_id}/comments", headers=devops, json={"body": "devops note"})
    assert r.status_code == 201


def test_devops_can_reassign_and_clear(client: TestClient, devops: dict, ana: dict):
    task_id = owned_task_id(client, ana, ANA_ID)
    r = client.patch(f"/api/tasks/{task_id}", headers=devops, json={"assigneeId": BEN_ID})
    assert r.status_code == 200
    assert r.json()["assigneeId"] == BEN_ID
    # old owner loses access after reassignment
    assert client.patch(f"/api/tasks/{task_id}", headers=ana, json={"title": "x"}).status_code == 403
    r = client.patch(f"/api/tasks/{task_id}", headers=devops, json={"assigneeId": None})
    assert r.json()["assigneeId"] is None


def test_devops_reassign_to_non_developer_is_422(client: TestClient, devops: dict, ana: dict):
    task_id = owned_task_id(client, ana, ANA_ID)
    assert client.patch(f"/api/tasks/{task_id}", headers=devops, json={"assigneeId": "u-devops"}).status_code == 422
