import hashlib
import hmac
import os
import secrets
import time

COOKIE_NAME = "children_session"
SESSION_SECONDS = 7 * 24 * 60 * 60


def configuration():
    password_hash = os.environ.get("AUTH_PASSWORD_HASH", "")
    secret = os.environ.get("AUTH_SECRET", "")
    if not password_hash or len(secret) < 32:
        raise RuntimeError("Set AUTH_PASSWORD_HASH and AUTH_SECRET before starting the server")
    return password_hash, secret.encode()


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 600_000)
    return f"{salt}${digest.hex()}"


def verify_password(password, stored):
    try:
        salt, expected = stored.split("$", 1)
        actual = hash_password(password, salt).split("$", 1)[1]
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_session(secret):
    expires = str(int(time.time()) + SESSION_SECONDS)
    signature = hmac.new(secret, expires.encode(), hashlib.sha256).hexdigest()
    return f"{expires}.{signature}"


def valid_session(token, secret):
    try:
        expires, signature = token.split(".", 1)
        if int(expires) < time.time():
            return False
        expected = hmac.new(secret, expires.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature, expected)
    except (ValueError, AttributeError):
        return False
