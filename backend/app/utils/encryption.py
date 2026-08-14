"""Symmetric encryption for secrets stored at rest (e.g. the Gmail OAuth
refresh token on `users.google_refresh_token_encrypted`), keyed by the
single `MASTER_ENCRYPTION_KEY` (Phase 2 §15 — supersedes the earlier
per-credential key design).

Never stores the key itself anywhere near the encrypted data — it's a
boot-time setting (`app/config/settings.py`), not a DB value.
"""

from __future__ import annotations

from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.config.settings import get_settings


class EncryptionError(Exception):
    pass


@lru_cache
def _fernet() -> Fernet:
    settings = get_settings()
    return Fernet(settings.master_encryption_key.encode("utf-8"))


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise EncryptionError("Stored value could not be decrypted — key mismatch?") from exc
