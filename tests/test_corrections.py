"""Run with: .venv/bin/python tests/test_corrections.py from the repository root."""

import os
from pathlib import Path
import sys
import tempfile

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.app.auth import hash_password


def main():
    os.environ["AUTH_USERNAME"] = "admin"
    os.environ["AUTH_PASSWORD_HASH"] = hash_password("test-password")
    os.environ["AUTH_SECRET"] = "c" * 64
    with tempfile.TemporaryDirectory() as directory:
        os.chdir(directory)
        from backend.app.main import app

        client = TestClient(app)
        assert client.post("/api/login", json={"username": "admin", "password": "test-password"}).status_code == 200
        first = client.post("/api/children", json={"name": "小星", "birth_date": "2025-01-01"}).json()["id"]
        second = client.post("/api/children", json={"name": "小月", "birth_date": "2025-02-01"}).json()["id"]

        entry = client.post("/api/entries", json={"child_ids": [first], "title": "旧标题", "content": "旧文字"}).json()
        changed = client.patch(f"/api/entries/{entry['id']}", json={
            "child_ids": [first, second], "title": "新标题", "content": "新文字",
            "occurred_at": "2025-03-01T12:00:00", "kind": "milestone",
        })
        assert changed.status_code == 200, changed.text
        assert changed.json()["title"] == "新标题" and changed.json()["child_ids"] == [first, second]
        assert client.patch(f"/api/entries/{entry['id']}", json={"title": None, "content": ""}).status_code == 422
        assert client.get("/api/entries").json()[0]["title"] == "新标题"
        assert client.patch(f"/api/entries/{entry['id']}", json={
            "media_url": "/static_uploads/" + "a" * 32 + ".jpg", "media_type": "image",
        }).status_code == 200
        assert client.patch(f"/api/entries/{entry['id']}", json={
            "media_url": None, "media_type": None,
        }).json()["media_url"] is None

        checkup = client.post("/api/checkups", json={
            "child_id": first, "checkup_date": "2025-03-02T12:00:00", "weight_kg": 4.2,
            "media_url": "/static_uploads/" + "b" * 32 + ".jpg",
        }).json()
        growth = client.get("/api/growth").json()[0]
        assert client.patch(f"/api/growth/{growth['id']}", json={"weight_kg": 5.0}).status_code == 409
        updated = client.patch(f"/api/checkups/{checkup['id']}", json={
            "child_id": second, "checkup_date": "2025-03-03T12:00:00", "weight_kg": 4.4,
            "height_cm": 53.1, "hospital": "保健院", "media_url": None,
        })
        assert updated.status_code == 200, updated.text
        assert updated.json()["media_url"] is None
        linked = client.get("/api/growth").json()[0]
        assert linked["id"] == growth["id"] and linked["child_id"] == second
        assert linked["weight_kg"] == 4.4 and linked["height_cm"] == 53.1
        assert linked["measured_at"].startswith("2025-03-03") and linked["note"] == "保健院"
        assert client.patch(f"/api/checkups/{checkup['id']}", json={"weight_kg": None, "height_cm": None}).status_code == 200
        assert client.get("/api/growth").json() == []
        assert client.patch(f"/api/checkups/{checkup['id']}", json={"head_cm": 37.2}).status_code == 200
        assert client.get("/api/growth").json()[0]["head_cm"] == 37.2
        assert client.patch(f"/api/checkups/{checkup['id']}", json={"checkup_date": None}).status_code == 422

        manual = client.post("/api/growth", json={"child_id": first, "weight_kg": 5.1}).json()
        fixed = client.patch(f"/api/growth/{manual['id']}", json={
            "child_id": second, "weight_kg": 5.3, "measured_at": "2025-03-05T12:00:00",
        })
        assert fixed.status_code == 200, fixed.text
        assert fixed.json()["child_id"] == second and fixed.json()["weight_kg"] == 5.3
        assert client.patch(f"/api/growth/{manual['id']}", json={"weight_kg": None}).status_code == 422
        assert client.get("/api/growth", params={"child_id": second}).json()[-1]["weight_kg"] == 5.3

        jaundice = client.post("/api/jaundice", json={"child_id": first, "value": 8.2}).json()
        corrected = client.patch(f"/api/jaundice/{jaundice['id']}", json={
            "child_id": second, "record_date": "2025-02-03T12:00:00", "value": 7.9, "note": "额头",
        })
        assert corrected.status_code == 200, corrected.text
        assert corrected.json()["child_id"] == second and corrected.json()["value"] == 7.9
        assert client.patch(f"/api/jaundice/{jaundice['id']}", json={"value": None}).status_code == 422
    print("correction flow passed")


if __name__ == "__main__":
    main()
