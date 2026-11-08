"""Run with: .venv/bin/python tests/test_care.py"""
import os
from pathlib import Path
import sys
import tempfile

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.app.auth import hash_password


def main():
    os.environ.update(AUTH_USERNAME="admin", AUTH_PASSWORD_HASH=hash_password("test-password"), AUTH_SECRET="c" * 64)
    os.environ.pop("OPENAI_API_KEY", None)
    with tempfile.TemporaryDirectory() as directory:
        os.chdir(directory)
        from backend.app.main import app
        client = TestClient(app)
        assert client.get("/api/care?child_id=1&day=2026-11-08").status_code == 401
        assert client.post("/api/care/transcribe", files={"file": ("voice.m4a", b"audio")}).status_code == 401
        assert client.get("/api/care/voice-status").status_code == 401
        for path in ("/assets/manifest.webmanifest", "/assets/app-icon-192.png"):
            assert client.get(path, follow_redirects=False).status_code == 303
        assert client.post("/api/login", json={"username": "admin", "password": "test-password"}).status_code == 200
        child_id = client.get("/api/children").json()[0]["id"]
        assert client.get("/api/care/voice-status").json() == {"server_recognition": False}
        payload = {"child_id": child_id, "kind": "feeding", "occurred_at": "2026-11-08T15:30", "amount_ml": 120, "note": "母乳后补奶"}
        created = client.post("/api/care", json=payload)
        assert created.status_code == 200, created.text
        item = created.json()
        assert item["amount_ml"] == 120
        assert len(client.get(f"/api/care?child_id={child_id}&day=2026-11-08").json()) == 1
        assert client.get(f"/api/care?child_id={child_id}&day=2026-11-09").json() == []
        assert client.post("/api/care", json={**payload, "kind": "bad"}).status_code == 422
        assert client.post("/api/care", json={**payload, "child_id": 9999}).status_code == 404
        changed = client.patch(f"/api/care/{item['id']}", json={"kind": "poop", "occurred_at": "2026-11-08T17:20"})
        assert changed.status_code == 200 and changed.json()["kind"] == "poop"
        assert changed.json()["amount_ml"] is None
        disabled = client.post("/api/care/transcribe", files={"file": ("voice.m4a", b"audio", "audio/mp4")})
        assert disabled.status_code == 503
        assert client.delete(f"/api/care/{item['id']}").status_code == 204
        assert client.get(f"/api/care?child_id={child_id}&day=2026-11-08").json() == []
        assert client.get("/assets/app.js").status_code == 200
        assert client.get("/assets/manifest.webmanifest").json()["display"] == "standalone"
        assert client.get("/assets/app-icon-192.png").content.startswith(b"\x89PNG")
        client.post("/api/logout")
        assert client.get("/assets/app.js", follow_redirects=False).status_code == 303
    print("care flow passed")


if __name__ == "__main__":
    main()
