"""JWT issuance/verification, password hashing, and refresh tokens.

Security boundary rule (Part 3 §32): JWT secrets and tokens are handled
only here and in app/api/deps.py / app/api/v1/auth.py — never logged,
never passed through the general logging context.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from flames_shared.enums import UserRole
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config.settings import get_settings

# Argon2 preferred (Part 5 §58), bcrypt kept so existing bcrypt hashes
# still verify during a migration rather than locking users out.
_pwd_context = CryptContext(schemes=["argon2", "bcrypt"], default="argon2", deprecated="auto")

REFRESH_TOKEN_EXPIRE_DAYS = 30


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, role: UserRole) -> str:
    """`subject` is the user's id (str(UUID)) — never email/PII in the
    payload (Phase 2 §07: JWTs are base64, not encrypted, and often end
    up in logs)."""
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "role": role.value,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, object] | None:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
    if payload.get("type") != "access":
        return None
    return payload


def create_refresh_token() -> tuple[str, str, datetime]:
    """Returns (raw_token, token_hash, expires_at). Only the hash is ever
    persisted (Part 5 §58: "refresh tokens are securely stored (hashed in
    DB) and revocable") — the raw token goes to the client once and is
    never stored server-side."""
    raw_token = secrets.token_urlsafe(48)
    expires_at = datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    return raw_token, hash_refresh_token(raw_token), expires_at


def hash_refresh_token(raw_token: str) -> str:
    # A refresh token is already a high-entropy random secret, unlike a
    # user password, so a fast deterministic hash (for DB lookup by hash)
    # is appropriate here — argon2/bcrypt are for low-entropy secrets.
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
