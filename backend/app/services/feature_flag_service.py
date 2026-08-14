"""DB-backed feature-flag reads/writes (Phase 2 §08: this is the
`FeatureFlagService`/`SettingsRepository` layer for *runtime-overridable*
settings — distinct from `SettingsService`, which is boot-time env config
only). A flag not yet in the `feature_flags` table falls back to its
`ENABLE_*` env default.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.repositories.feature_flag_repository import FeatureFlagRepository

FLAG_KEYS = (
    "enable_playwright",
    "enable_gmail",
    "enable_telegram",
    "enable_ai_scoring",
    "enable_auto_apply",
    "enable_dashboard",
    "enable_screenshots",
    "enable_resume_generator",
    "enable_interview_preparation",
)


class FeatureFlagService:
    def __init__(self, db: AsyncSession, repo: FeatureFlagRepository) -> None:
        self._db = db
        self._repo = repo

    async def get_all(self) -> dict[str, bool]:
        settings = get_settings()
        flags: dict[str, bool] = {}
        for key in FLAG_KEYS:
            row = await self._repo.get_by_key(key)
            flags[key] = row.enabled if row is not None else getattr(settings, key)
        return flags

    async def set(self, key: str, enabled: bool) -> None:
        if key not in FLAG_KEYS:
            raise KeyError(f"Unknown feature flag: {key}")
        existing = await self._repo.get_by_key(key)
        if existing is None:
            await self._repo.create(key=key, enabled=enabled)
        else:
            existing.enabled = enabled
        await self._db.commit()


def get_feature_flag_service(db: AsyncSession) -> FeatureFlagService:
    return FeatureFlagService(db=db, repo=FeatureFlagRepository(db))
