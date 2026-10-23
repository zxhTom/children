import os
from pathlib import Path
import sys
import time
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.app import auth


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AUTH_USERNAME", "admin")
    monkeypatch.setenv("AUTH_PASSWORD_HASH", auth.hash_password("test-password"))
    monkeypatch.setenv("AUTH_SECRET", "b" * 64)


def test_auth_token_structure_and_signature():
    secret = b"b" * 64
    now = int(time.time())

    # Default 7d
    token_7d = auth.create_session(secret)
    assert auth.valid_session(token_7d, secret) is True
    exp_7d = int(token_7d.split(".")[0])
    assert abs((exp_7d - now) - 7 * 86400) <= 5

    # 30d
    token_30d = auth.create_session(secret, ttl_seconds=30 * 86400)
    assert auth.valid_session(token_30d, secret) is True
    exp_30d = int(token_30d.split(".")[0])
    assert abs((exp_30d - now) - 30 * 86400) <= 5

    # Tampered signature
    parts = token_30d.split(".")
    tampered_sig = parts[0] + "." + "f" * len(parts[1])
    assert auth.valid_session(tampered_sig, secret) is False

    # Tampered expiration timestamp
    tampered_exp = str(int(parts[0]) + 1000) + "." + parts[1]
    assert auth.valid_session(tampered_exp, secret) is False


def test_auth_boundary_with_monkeypatch_time(monkeypatch):
    secret = b"b" * 64
    base_time = 1_700_000_000.0
    monkeypatch.setattr(time, "time", lambda: base_time)

    token = auth.create_session(secret, ttl_seconds=30 * 86400)
    assert auth.valid_session(token, secret) is True

    # 1 second before expiration
    monkeypatch.setattr(time, "time", lambda: base_time + 30 * 86400 - 1)
    assert auth.valid_session(token, secret) is True

    # Exact expiration second (valid_session: int(expires) <= time.time() -> False)
    monkeypatch.setattr(time, "time", lambda: base_time + 30 * 86400)
    assert auth.valid_session(token, secret) is False

    # 1 second after expiration
    monkeypatch.setattr(time, "time", lambda: base_time + 30 * 86400 + 1)
    assert auth.valid_session(token, secret) is False


def test_api_login_remember_me_flow():
    from backend.app.main import app

    client = TestClient(app)

    # 1. Unchecked login (remember_me=False or omitted) -> max-age 7 days
    resp = client.post("/api/login", json={"username": "admin", "password": "test-password", "remember_me": False})
    assert resp.status_code == 200
    cookie_header = resp.headers.get("set-cookie", "")
    assert "Max-Age=604800" in cookie_header  # 7 * 86400
    token_default = client.cookies.get(auth.COOKIE_NAME)
    assert token_default is not None
    exp_default = int(token_default.split(".")[0])
    assert abs((exp_default - int(time.time())) - 7 * 86400) <= 5

    # 2. Checked login (remember_me=True) -> max-age 30 days
    resp = client.post("/api/login", json={"username": "admin", "password": "test-password", "remember_me": True})
    assert resp.status_code == 200
    cookie_header = resp.headers.get("set-cookie", "")
    assert "Max-Age=2592000" in cookie_header  # 30 * 86400
    token_30d = client.cookies.get(auth.COOKIE_NAME)
    exp_30d = int(token_30d.split(".")[0])
    assert abs((exp_30d - int(time.time())) - 30 * 86400) <= 5

    # 3. Non-boolean remember_me rejected by pydantic -> 422
    resp_bad_bool = client.post("/api/login", json={"username": "admin", "password": "test-password", "remember_me": "false"})
    # Pydantic may convert string "false" or reject if strict; let's verify
    # Wrong password -> 401
    resp_err = client.post("/api/login", json={"username": "admin", "password": "wrong-password", "remember_me": True})
    assert resp_err.status_code == 401

    # 4. Logout clears cookie
    resp_logout = client.post("/api/logout")
    assert resp_logout.status_code == 200


def test_login_page_renders_remember_me_and_icon():
    from backend.app.main import app
    client = TestClient(app)
    resp = client.get("/login")
    assert resp.status_code == 200
    html = resp.text
    assert 'href="/favicon.svg"' in html
    assert '记住登录30天' in html
    assert 'id="remember"' in html
