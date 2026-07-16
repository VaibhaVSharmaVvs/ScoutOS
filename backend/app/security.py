"""Password hashing and JWT helpers for the auth layer."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings

# bcrypt hashes only the first 72 bytes; truncate explicitly (bcrypt 4.x raises
# otherwise). Using the bcrypt lib directly — passlib 1.7.x breaks on bcrypt 4.x.
_MAX_BCRYPT_BYTES = 72


def _to_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:_MAX_BCRYPT_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_to_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_to_bytes(password), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject: str) -> str:
    s = get_settings()
    expire = datetime.now(UTC) + timedelta(minutes=s.jwt_expire_minutes)
    return jwt.encode({"sub": subject, "exp": expire}, s.jwt_secret, algorithm=s.jwt_algorithm)


def decode_access_token(token: str) -> dict | None:
    s = get_settings()
    try:
        return jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])
    except JWTError:
        return None
