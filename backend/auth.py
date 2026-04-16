import hashlib
import hmac
import json
import base64
import time
import os

SECRET = os.environ.get("JWT_SECRET", "life-tracker-secret-key-change-in-prod")


def hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000).hex()
    return f"{salt}${h}"


def verify_password(password: str, stored: str) -> bool:
    salt, h = stored.split("$")
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000).hex() == h


def create_token(user_id: int, username: str) -> str:
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip("=")
    payload_data = {"sub": user_id, "username": username, "exp": int(time.time()) + 86400 * 7}
    payload = base64.urlsafe_b64encode(json.dumps(payload_data).encode()).decode().rstrip("=")
    sig_input = f"{header}.{payload}".encode()
    signature = base64.urlsafe_b64encode(
        hmac.new(SECRET.encode(), sig_input, hashlib.sha256).digest()
    ).decode().rstrip("=")
    return f"{header}.{payload}.{signature}"


def decode_token(token: str) -> dict | None:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header, payload, signature = parts
        sig_input = f"{header}.{payload}".encode()
        expected = base64.urlsafe_b64encode(
            hmac.new(SECRET.encode(), sig_input, hashlib.sha256).digest()
        ).decode().rstrip("=")
        if not hmac.compare_digest(signature, expected):
            return None
        padding = 4 - len(payload) % 4
        payload_data = json.loads(base64.urlsafe_b64decode(payload + "=" * padding))
        if payload_data.get("exp", 0) < time.time():
            return None
        return payload_data
    except Exception:
        return None
