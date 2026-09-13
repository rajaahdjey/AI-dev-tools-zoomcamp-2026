"""Backend serves the built SPA without shadowing /api/*."""

from fastapi.testclient import TestClient

from app.main import create_app


def test_serves_spa_and_keeps_api_json(tmp_path, monkeypatch):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>kanban</html>")
    (dist / "assets" / "app.js").write_text("console.log(1)")
    monkeypatch.setenv("FRONTEND_DIR", str(dist))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/test.db")
    client = TestClient(create_app())
    try:
        home = client.get("/")
        assert home.status_code == 200
        assert "kanban" in home.text
        assert "text/html" in home.headers["content-type"]

        js = client.get("/assets/app.js")
        assert js.status_code == 200

        # API routes still win and keep the {"error"} shape.
        r = client.get("/api/tasks")
        assert r.status_code == 401
        assert set(r.json()) == {"error"}

        missing = client.get("/no-such-page")
        assert missing.status_code == 404
        assert set(missing.json()) == {"error"}
    finally:
        client.app.state.store.close()


def test_no_frontend_dir_mounts_nothing(tmp_path, monkeypatch):
    monkeypatch.setenv("FRONTEND_DIR", str(tmp_path / "absent"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/test.db")
    client = TestClient(create_app())
    try:
        assert client.get("/").status_code == 404
    finally:
        client.app.state.store.close()
