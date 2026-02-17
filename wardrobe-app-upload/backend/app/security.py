import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from .config import get_settings

settings = get_settings()
PBKDF2_ITERATIONS = 120_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return "pbkdf2_sha256${iterations}${salt}${hash}".format(
        iterations=PBKDF2_ITERATIONS,
        salt=base64.b64encode(salt).decode("ascii"),
        hash=base64.b64encode(hashed).decode("ascii"),
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_raw, salt_raw, hash_raw = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False

        iterations = int(iterations_raw)
        salt = base64.b64decode(salt_raw.encode("ascii"))
        expected = base64.b64decode(hash_raw.encode("ascii"))
    except Exception:
        return False

    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual, expected)


def create_access_token(subject: str, expires_minutes: int | None = None) -> str:
    expire_delta = timedelta(minutes=expires_minutes or settings.access_token_expire_minutes)
    payload = {
        "sub": subject,
        "exp": datetime.now(tz=timezone.utc) + expire_delta,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("invalid token") from exc


def create_oauth_state(provider: str, extra: dict | None = None) -> str:
    payload = {
        "provider": provider,
        "exp": datetime.now(tz=timezone.utc) + timedelta(minutes=10),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_oauth_state(state: str) -> dict:
    try:
        return jwt.decode(state, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("invalid state") from exc
