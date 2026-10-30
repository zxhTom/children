"""Run with: .venv/bin/python tests/test_import_csv.py from the repository root."""

import csv
import io
import os
from pathlib import Path
import sys
import tempfile

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.app.auth import hash_password
from backend.app.import_csv import HEADERS


def csv_bytes(rows):
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(HEADERS)
    writer.writerows(rows)
    return ("\ufeff" + output.getvalue()).encode("utf-8")


def upload(client, action, child_id, data, file_hash=None):
    form = {"child_id": child_id}
    if file_hash is not None:
        form["file_hash"] = file_hash
    return client.post(f"/api/import/{action}", data=form,
                       files={"file": ("history.csv", data, "text/csv")})


def main():
    os.environ["AUTH_USERNAME"] = "admin"
    os.environ["AUTH_PASSWORD_HASH"] = hash_password("test-password")
    os.environ["AUTH_SECRET"] = "d" * 64
    with tempfile.TemporaryDirectory() as directory:
        os.chdir(directory)
        from backend.app.main import app

        client = TestClient(app)
        assert client.get("/api/import/template").status_code == 401
        assert client.post("/api/import/preview", data={"child_id": 1},
                           files={"file": ("history.csv", csv_bytes([]), "text/csv")}).status_code == 401
        assert client.post("/api/login", json={"username": "admin", "password": "test-password"}).status_code == 200
        template = client.get("/api/import/template")
        assert template.status_code == 200
        assert template.content.startswith(b"\xef\xbb\xbf")
        assert list(csv.reader(io.StringIO(template.content.decode("utf-8-sig")))) == [HEADERS]
        child_id = client.post("/api/children", json={"name": "小星", "birth_date": "2020-09-26"}).json()["id"]
        bad = csv_bytes([
            ["回忆", "2020-10-01", "第一次出门", "一起散步", "妈妈", "", "", "", "", ""],
            ["测量", "2021-02-30", "", "", "", "8.5", "", "", "", ""],
        ])
        invalid = upload(client, "preview", child_id, bad)
        assert invalid.status_code == 422
        assert "第 3 行" in invalid.json()["detail"]["errors"][0]
        assert client.get("/api/entries").json() == []

        good = csv_bytes([
            ["回忆", "2020-10-01", "第一次出门", "一起散步", "妈妈", "", "", "", "", ""],
            ["关键时刻", "2021-09-26", "一岁生日", "吹蜡烛", "爸爸", "", "", "", "", ""],
            ["体检", "2022-01-03", "", "定期检查", "", "11.2", "80.1", "", "社区医院", "2022-02-03"],
            ["测量", "2023-02-01", "", "在家测量", "", "13.5", "", "", "", ""],
        ])
        preview = upload(client, "preview", child_id, good)
        assert preview.status_code == 200, preview.text
        assert preview.json()["total"] == 4
        assert preview.json()["counts"] == {"回忆": 1, "关键时刻": 1, "体检": 1, "测量": 1}
        assert upload(client, "commit", child_id, good, "wrong").status_code == 409
        committed = upload(client, "commit", child_id, good, preview.json()["file_hash"])
        assert committed.status_code == 200, committed.text
        assert committed.json()["created"] == 4
        assert upload(client, "commit", child_id, good, preview.json()["file_hash"]).status_code == 409
        entries = client.get("/api/entries", params={"child_id": child_id}).json()
        assert len(entries) == 2
        assert {item["kind"] for item in entries} == {"diary", "milestone"}
        checkups = client.get("/api/checkups", params={"child_id": child_id}).json()
        assert len(checkups) == 1 and checkups[0]["weight_kg"] == 11.2
        growth = client.get("/api/growth", params={"child_id": child_id}).json()
        assert len(growth) == 2
        assert sum(item["checkup_id"] is not None for item in growth) == 1
    print("CSV import flow passed")


if __name__ == "__main__":
    main()
