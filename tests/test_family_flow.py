"""Run with: python3 tests/test_family_flow.py (from the repository root)."""

import os
from pathlib import Path
import sqlite3
import sys
import tempfile

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.app.auth import hash_password


LEGACY_SCHEMA = """
CREATE TABLE journal_entries (id INTEGER PRIMARY KEY, perspective VARCHAR, author VARCHAR,
    content TEXT, created_at DATETIME, media_url VARCHAR, media_type VARCHAR, tags VARCHAR);
CREATE TABLE medical_checkups (id INTEGER PRIMARY KEY, perspective VARCHAR, checkup_date DATETIME,
    hospital VARCHAR, report_text TEXT, media_url VARCHAR, abnormal_indicators TEXT,
    next_checkup_date DATETIME, next_checkup_notes TEXT);
CREATE TABLE jaundice_records (id INTEGER PRIMARY KEY, perspective VARCHAR, record_date DATETIME,
    value FLOAT, note VARCHAR);
INSERT INTO journal_entries VALUES (1, 'daughter', '妈妈', '第一次微笑', '2026-10-01 12:00:00', NULL, NULL, NULL);
INSERT INTO journal_entries VALUES (2, 'parent', '爸爸', '一起散步', '2026-10-02 12:00:00', NULL, NULL, NULL);
INSERT INTO medical_checkups VALUES (1, 'son', '2026-10-03 12:00:00', '社区医院', '旧体检', NULL, NULL, NULL, NULL);
INSERT INTO jaundice_records VALUES (1, 'daughter', '2026-10-04 12:00:00', 8.2, '额头');
"""


def main():
    os.environ["AUTH_USERNAME"] = "admin"
    os.environ["AUTH_PASSWORD_HASH"] = hash_password("test-password")
    os.environ["AUTH_SECRET"] = "a" * 64
    with tempfile.TemporaryDirectory() as directory:
        os.chdir(directory)
        with sqlite3.connect("children_diary.db") as connection:
            connection.executescript(LEGACY_SCHEMA)

        from backend.app.main import app
        from backend.app.migrations import initialize_database

        client = TestClient(app)
        assert client.get("/api/children").status_code == 401
        assert client.post("/api/login", json={"username": "admin", "password": "test-password"}).status_code == 200
        children = client.get("/api/children").json()
        assert len(children) == 2
        daughter = next(child for child in children if child["nickname"] == "妹妹")
        son = next(child for child in children if child["nickname"] == "哥哥")
        entries = client.get("/api/entries").json()
        assert next(entry for entry in entries if entry["id"] == 1)["child_ids"] == [daughter["id"]]
        assert next(entry for entry in entries if entry["id"] == 2)["child_ids"] == []
        assert client.get("/api/checkups").json()[0]["child_id"] == son["id"]
        assert client.get("/api/jaundice").json()[0]["child_id"] == daughter["id"]
        assert len(list(Path(directory).glob("*.pre-multichild-*.bak"))) == 1
        initialize_database()
        assert len(list(Path(directory).glob("*.pre-multichild-*.bak"))) == 1

        new_child = client.post("/api/children", json={"name": "小星", "birth_date": "2024-03-06"})
        assert new_child.status_code == 200, new_child.text
        third_id = new_child.json()["id"]
        linked = client.post("/api/entries", json={
            "child_ids": [daughter["id"], third_id], "kind": "diary", "title": "第一次一起玩",
            "content": "一起搭积木", "occurred_at": "2026-10-10T12:00:00",
        })
        assert linked.status_code == 200, linked.text
        linked_id = linked.json()["id"]
        assert linked_id in [entry["id"] for entry in client.get("/api/entries", params={"child_id": third_id}).json()]
        assert linked_id in [entry["id"] for entry in client.get("/api/entries", params={"child_id": daughter["id"]}).json()]
        assert linked_id not in [entry["id"] for entry in client.get("/api/entries", params={"child_id": son["id"]}).json()]
        suggestions = client.get("/api/moments/suggestions").json()
        assert linked_id in [item["id"] for item in suggestions]
        assert client.patch(f"/api/entries/{linked_id}", json={"kind": "milestone"}).status_code == 200

        checkup = client.post("/api/checkups", json={
            "child_id": third_id, "checkup_date": "2026-10-11T12:00:00", "weight_kg": 12.4,
            "height_cm": 89.5, "hospital": "社区医院",
        })
        assert checkup.status_code == 200, checkup.text
        growth = client.get("/api/growth", params={"child_id": third_id}).json()
        assert len(growth) == 1 and growth[0]["checkup_id"] == checkup.json()["id"]
        assert growth[0]["weight_kg"] == 12.4

        story = client.post("/api/stories/generate", json={
            "child_ids": [daughter["id"], third_id], "from_date": "2026-10-10", "to_date": "2026-10-10",
        })
        assert story.status_code == 200, story.text
        assert story.json()["stats"]["records"] == 1
        assert story.json()["stats"]["shared"] == 1
        assert story.json()["stats"]["milestones"] == 1
        assert len(story.json()["sections"][0]["moments"][0]["children"]) == 2
        assert story.json()["stats"]["checkups"] == 0
        full_story = client.post("/api/stories/generate", json={
            "child_ids": [daughter["id"], third_id], "from_date": "2026-10-10", "to_date": "2026-10-11",
        })
        assert full_story.status_code == 200, full_story.text
        assert full_story.json()["stats"]["checkups"] == 1
        assert full_story.json()["stats"]["measurements"] == 1
        assert full_story.json()["health_notes"][0]["latest"]["weight_kg"] == 12.4
        assert client.post("/api/logout").status_code == 200
        assert client.get("/api/entries").status_code == 401
    print("family flow passed")


if __name__ == "__main__":
    main()
