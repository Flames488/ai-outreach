"""Idempotent seed script (Phase 2 §06) — safe to re-run, checks for
existing rows before inserting. Creates:

- The initial ADMIN user (`SEED_ADMIN_EMAIL`/`SEED_ADMIN_PASSWORD`) — not
  skippable, Telegram admin commands are unreachable without one.
- Default `feature_flags` rows, one per `ENABLE_*` setting.
- A starter set of `application_rules` so a fresh install isn't scoring
  with zero rules (a CRITICAL no-duplicates rule — structurally redundant
  with the DB unique-per-job-application constraint, but keeps the audit
  trail complete — and a REQUIRED conservative minimum-score rule the
  user can tune from day one).

Run via: `docker compose run --rm api uv run python scripts/seed.py`
"""

from __future__ import annotations

import asyncio
import logging

from app.auth.security import hash_password
from app.config.settings import get_settings
from app.database.session import session_scope
from app.models.user import User
from app.repositories.application_rule_repository import ApplicationRuleRepository
from app.repositories.feature_flag_repository import FeatureFlagRepository
from app.repositories.user_repository import UserRepository
from app.services.feature_flag_service import FLAG_KEYS
from flames_shared.enums import RuleOperator, RulePriorityTier, UserRole
from sqlalchemy.ext.asyncio import AsyncSession

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed")

DEFAULT_MIN_SCORE = 70


async def seed_admin_user(db: AsyncSession) -> User:
    settings = get_settings()
    users = UserRepository(db)
    existing = await users.get_by_email(settings.seed_admin_email)
    if existing is not None:
        logger.info("Admin user already exists: %s", settings.seed_admin_email)
        return existing

    if not settings.seed_admin_password:
        raise RuntimeError("SEED_ADMIN_PASSWORD is not set — cannot create the initial admin user.")

    user = await users.create(
        email=settings.seed_admin_email,
        password_hash=hash_password(settings.seed_admin_password),
        role=UserRole.ADMIN,
    )
    await db.commit()
    logger.info("Created admin user: %s", settings.seed_admin_email)
    return user


async def seed_feature_flags(db: AsyncSession) -> None:
    settings = get_settings()
    flags = FeatureFlagRepository(db)
    for key in FLAG_KEYS:
        existing = await flags.get_by_key(key)
        if existing is not None:
            continue
        await flags.create(
            key=key,
            enabled=getattr(settings, key),
            description=f"Default seeded from {key.upper()} env var.",
        )
        logger.info("Seeded feature flag: %s", key)
    await db.commit()


async def seed_application_rules(db: AsyncSession, user: User) -> None:
    rules = ApplicationRuleRepository(db)
    existing = await rules.list(user_id=user.id, limit=1)
    if existing:
        logger.info("application_rules already seeded for %s", user.email)
        return

    await rules.create(
        user_id=user.id,
        name="Daily application cap",
        description=(
            "Sanity ceiling so a bug can't queue an unbounded number of "
            "applications in one day. (True duplicate-application "
            "protection is structural — a DB unique constraint plus "
            "ApplicationService.create_application's own check — not "
            "expressible through this condition schema.)"
        ),
        priority_tier=RulePriorityTier.CRITICAL,
        condition={"field": "applications_today", "op": RuleOperator.LTE.value, "value": 50},
        enabled=True,
    )
    await rules.create(
        user_id=user.id,
        name="Minimum AI match score",
        description="Conservative default — tune from the dashboard once you have data.",
        priority_tier=RulePriorityTier.REQUIRED,
        condition={
            "field": "ai_score",
            "op": RuleOperator.GTE.value,
            "value": DEFAULT_MIN_SCORE,
        },
        enabled=True,
    )
    await db.commit()
    logger.info("Seeded starter application_rules for %s", user.email)


async def main() -> None:
    async with session_scope() as db:
        user = await seed_admin_user(db)
        await seed_feature_flags(db)
        await seed_application_rules(db, user)
    logger.info("Seed complete.")


if __name__ == "__main__":
    asyncio.run(main())
