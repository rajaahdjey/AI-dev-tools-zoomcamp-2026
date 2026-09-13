"""Persistence: file-DB isolation per test + restart durability."""

from fastapi.testclient import TestClient

from app.main import create_app
from .conftest import DEVOPS_ID, login


def test_database_url_env_selects_engine(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path}/custom.db"
    monkeypatch.setenv("DATABASE_URL", url)
    store = create_app(seed=False).state.store
    try:
        assert str(store.engine.url) == url
    finally:
        store.close()


def test_board_survives_restart_on_same_file(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/kanban.db")
    c1 = TestClient(create_app())
    devops = {"Authorization": f"Bearer {login(c1, DEVOPS_ID)}"}
    created = c1.post("/api/tasks", headers=devops, json={"title": "persist me"}).json()
    assert c1.post(f"/api/tasks/{created['id']}/comments", headers=devops,
                   json={"body": "still here"}).status_code == 201
    c1.app.state.store.close()

    c2 = TestClient(create_app(seed=False))
    try:
        fresh = {"Authorization": f"Bearer {login(c2, DEVOPS_ID)}"}
        tasks = {t["id"]: t for t in c2.get("/api/tasks", headers=fresh).json()}
        assert len(tasks) == 12  # 11 seeded + 1 created
        assert tasks[created["id"]]["comments"][0]["body"] == "still here"
        assert len(c2.get("/api/users", headers=fresh).json()) == 5
    finally:
        c2.app.state.store.close()
