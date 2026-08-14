"""CRUD for `RefreshToken`."""

from __future__ import annotations

from app.models.refresh_token import RefreshToken
from app.repositories.base_repository import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    model = RefreshToken

    async def get_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        result = await self.db.execute(
            self._base_query().where(RefreshToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def revoke(self, refresh_token: RefreshToken) -> None:
        refresh_token.revoked = True
        await self.db.flush()

    async def delete(self, refresh_token: RefreshToken) -> None:
        """`/auth/logout` — a hard delete, not soft: RefreshToken has no
        SoftDeleteMixin (it's a security-sensitive credential row, not
        business history worth retaining)."""
        await self.db.delete(refresh_token)
        await self.db.flush()
