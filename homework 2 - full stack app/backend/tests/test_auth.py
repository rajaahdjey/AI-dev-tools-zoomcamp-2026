"""Auth: login, bearer enforcement, logout."""

from fastapi.testclient import TestClient

from app.store import SEED_PASSWORD
from .conftest import ANA_ID, DEVOPS_ID, login


def test_login_returns_token_and_user(client: TestClient):
    r = client.post("/api/auth/login", json={"userId": DEVOPS_ID, "password": SEED_PASSWORD})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"] == {"id": DEVOPS_ID, "name": "Mira Shah", "role": "devops"}


def test_login_wrong_password_is_401_error_shape(client: TestClient):
    r = client.post("/api/auth/login", json={"userId": DEVOPS_ID, "password": "nope"})
    assert r.status_code == 401
    assert set(r.json()) == {"error"}


def test_login_unknown_user_is_401(client: TestClient):
    r = client.post("/api/auth/login", json={"userId": "u-ghost", "password": SEED_PASSWORD})
    assert r.status_code == 401


def test_missing_token_is_401_error_shape(client: TestClient):
    r = client.get("/api/tasks")
    assert r.status_code == 401
    assert set(r.json()) == {"error"}


def test_invalid_token_is_401(client: TestClient):
    r = client.get("/api/tasks", headers={"Authorization": "Bearer bogus"})
    assert r.status_code == 401


def test_users_list_needs_auth_but_returns_no_hashes(client: TestClient, devops: dict):
    assert client.get("/api/users").status_code == 401
    users = client.get("/api/users", headers=devops).json()
    assert len(users) == 5
    assert {u["role"] for u in users} == {"devops", "developer"}
    assert all(set(u) == {"id", "name", "role"} for u in users)


def test_logout_revokes_token(client: TestClient):
    token = login(client, ANA_ID)
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/tasks", headers=headers).status_code == 200
    assert client.post("/api/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/tasks", headers=headers).status_code == 401


def test_passwords_are_hashed_not_plaintext(client: TestClient):
    store = client.app.state.store
    hashed = store.get_user(DEVOPS_ID).password_hash
    assert hashed != SEED_PASSWORD
    assert "pbkdf2-sha256" in hashed
