"""Login, token issuance/refresh/revocation.

Used by both the HTTP auth router and (indirectly) Telegram's chat-ID
lookup path (`app/telegram/auth.py`), which resolves a `User` without
going through JWT at all (Phase 2 §07).
"""

from __future__ import annotations

from datetime import UTC, datetime

from flames_shared.enums import ErrorCode
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import (
    create_access_token,
    create_refresh_token,
    hash_refresh_token,
    verify_password,
)
from app.core.exceptions import FlamesAPIError
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TokenPair


class AuthService:
    def __init__(
        self, db: AsyncSession, users: UserRepository, refresh_tokens: RefreshTokenRepository
    ) -> None:
        self._db = db
        self._users = users
        self._refresh_tokens = refresh_tokens

    async def login(self, email: str, password: str) -> TokenPair:
        user = await self._users.get_by_email(email)
        if user is None or not user.is_active or not verify_password(password, user.password_hash):
            raise FlamesAPIError(401, ErrorCode.AUTH_INVALID_CREDENTIALS, "Invalid credentials")
        token_pair = await self._issue_token_pair(user)
        await self._db.commit()
        return token_pair

    async def refresh(self, raw_refresh_token: str) -> TokenPair:
        existing = await self._refresh_tokens.get_by_token_hash(
            hash_refresh_token(raw_refresh_token)
        )
        if existing is None or existing.revoked or existing.expires_at < datetime.now(UTC):
            raise FlamesAPIError(401, ErrorCode.AUTH_EXPIRED, "Refresh token invalid or expired")

        await self._refresh_tokens.revoke(existing)  # rotate: old token is single-use
        user = await self._users.get(existing.user_id)
        if user is None or not user.is_active:
            raise FlamesAPIError(401, ErrorCode.AUTH_INVALID_TOKEN, "User no longer exists")
        token_pair = await self._issue_token_pair(user)
        await self._db.commit()
        return token_pair

    async def logout(self, raw_refresh_token: str) -> None:
        existing = await self._refresh_tokens.get_by_token_hash(
            hash_refresh_token(raw_refresh_token)
        )
        if existing is not None:
            await self._refresh_tokens.delete(existing)
            await self._db.commit()

    async def _issue_token_pair(self, user: User) -> TokenPair:
        access_token = create_access_token(subject=str(user.id), role=user.role)
        raw_refresh_token, token_hash, expires_at = create_refresh_token()
        await self._refresh_tokens.create(
            user_id=user.id, token_hash=token_hash, expires_at=expires_at
        )
        return TokenPair(access_token=access_token, refresh_token=raw_refresh_token)


def get_auth_service(db: AsyncSession) -> AuthService:
    return AuthService(db=db, users=UserRepository(db), refresh_tokens=RefreshTokenRepository(db))
