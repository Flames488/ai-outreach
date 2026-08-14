"""Centralized configuration access (Part 5 §62) — business logic should
never read `.env`/`os.environ` directly; it goes through this instead.

Currently a thin wrapper over the env-backed Settings singleton. Once
runtime overrides are needed (the `settings` table, Part 4 §37), this is
the single place a DB lookup gets added — callers never change.
"""

from __future__ import annotations

from typing import Any

from app.config.settings import Settings, get_settings


class SettingsService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def get(self, key: str) -> Any:
        return getattr(self._settings, key.lower())


def get_settings_service() -> SettingsService:
    return SettingsService(settings=get_settings())
