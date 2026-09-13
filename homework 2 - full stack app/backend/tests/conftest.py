"""Shared fixtures: fresh seeded app per test + login helpers."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.store import SEED_PASSWORD

DEVOPS_ID = "u-devops"
ANA_ID = "u-ana"  # owns t-103, t-105, t-110
BEN_ID = "u-ben"  # owns t-104, t-107
CLEO_ID = "u-cleo"  # owns t-102, t-108

@pytest.fixture
def client(monkeypatch, tmp_path) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/test.db")
    app_client = TestClient(create_app())
    yield app_client
    app_client.app.state.store.close()


def login(client: TestClient, user_id: str, password: str = SEED_PASSWORD) -> str:
    r = client.post("/api/auth/login", json={"userId": user_id, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def auth_headers(client: TestClient, user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {login(client, user_id)}"}


@pytest.fixture
def devops(client: TestClient) -> dict[str, str]:
    return auth_headers(client, DEVOPS_ID)


@pytest.fixture
def ana(client: TestClient) -> dict[str, str]:
    return auth_headers(client, ANA_ID)


@pytest.fixture
def ben(client: TestClient) -> dict[str, str]:
    return auth_headers(client, BEN_ID)


def owned_task_id(client: TestClient, headers: dict[str, str], owner_id: str) -> str:
    tasks = client.get("/api/tasks", headers=headers).json()
    mine = [t for t in tasks if t["assigneeId"] == owner_id]
    assert mine, f"no seeded task owned by {owner_id}"
    return mine[0]["id"]
