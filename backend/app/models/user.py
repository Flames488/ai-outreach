"""`users`.

Login validates against this table's `password_hash` (see
`app/services/auth_service.py`) — `scripts/seed.py` creates the initial
ADMIN row from `SEED_ADMIN_EMAIL`/`SEED_ADMIN_PASSWORD`.
"""

from __future__ import annotations

from datetime import datetime

from flames_shared.enums import UserRole
from sqlalchemy import Boolean, DateTime, String
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    telegram_chat_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    telegram_username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        SqlEnum(UserRole, name="user_role", native_enum=True), default=UserRole.ADMIN
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Gmail OAuth (Phase 2 §15) — Fernet-encrypted via MASTER_ENCRYPTION_KEY
    # (app/utils/encryption.py), never the raw refresh token.
    google_refresh_token_encrypted: Mapped[str | None] = mapped_column(String(500), nullable=True)
    gmail_connected: Mapped[bool] = mapped_column(Boolean, default=False)
    gmail_last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
