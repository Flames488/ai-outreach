"""AI business logic — the only module allowed to talk to an AI provider.

Wraps every provider call with rate limiting (Redis, Phase 2 §14 — guards
Groq/DeepSeek's request-per-minute limits) and usage logging
(`ai_usage_logs`) so exhaustion is visible before it happens. Other
services depend on AIService, never on a provider class or the
`openai`/vendor package directly — swapping providers means changing
`app/ai/registry.py`, nothing else. Never called synchronously from a
route (Part 6 §72) — only from `app/tasks/ai_tasks.py`.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeVar

from flames_shared.dto import (
    CoverLetterDraft,
    EmailClassificationResult,
    JobPosting,
    MatchResult,
    TelegramIntent,
)
from flames_shared.enums import AITaskType, ErrorCode
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base_provider import AIResponseError
from app.ai.provider import AIProvider
from app.ai.registry import get_ai_provider
from app.config.settings import get_settings
from app.core.exceptions import FlamesAPIError
from app.core.rate_limit import enforce_rate_limit
from app.models.ai_usage_log import AIUsageLog
from app.repositories.ai_usage_log_repository import AIUsageLogRepository

T = TypeVar("T")

AI_RATE_LIMIT_WINDOW_SECONDS = 60


class AIService:
    def __init__(
        self,
        db: AsyncSession,
        provider: AIProvider,
        usage_log_repository: AIUsageLogRepository,
        provider_name: str,
        model: str,
        rate_limit_per_minute: int,
    ) -> None:
        self._db = db
        self._provider = provider
        self._usage_logs = usage_log_repository
        self._provider_name = provider_name
        self._model = model
        self._rate_limit_per_minute = rate_limit_per_minute

    async def analyze_job(self, job: JobPosting) -> dict[str, object]:
        return await self._call(AITaskType.JOB_ANALYSIS, self._provider.analyze_job, job)

    async def score_match(self, job: JobPosting, cv_profile: dict[str, object]) -> MatchResult:
        return await self._call(
            AITaskType.JOB_MATCHING, self._provider.score_match, job, cv_profile
        )

    async def generate_cover_letter(
        self, job: JobPosting, cv_profile: dict[str, object]
    ) -> CoverLetterDraft:
        return await self._call(
            AITaskType.COVER_LETTER, self._provider.generate_cover_letter, job, cv_profile
        )

    async def classify_email(self, email_content: str) -> EmailClassificationResult:
        return await self._call(
            AITaskType.EMAIL_CLASSIFICATION, self._provider.classify_email, email_content
        )

    async def answer_question(self, question: str, cv_profile: dict[str, object]) -> str:
        return await self._call(
            AITaskType.APPLICATION_ANSWER, self._provider.answer_question, question, cv_profile
        )

    async def interpret_telegram_message(
        self, message: str, available_commands: dict[str, str]
    ) -> TelegramIntent:
        return await self._call(
            AITaskType.TELEGRAM_ASSISTANT,
            self._provider.interpret_telegram_message,
            message,
            available_commands,
        )

    async def _call(
        self, task_type: AITaskType, func: Callable[..., Awaitable[T]], *args: object
    ) -> T:
        await enforce_rate_limit(
            key=f"ratelimit:ai:{self._provider_name}",
            max_attempts=self._rate_limit_per_minute,
            window_seconds=AI_RATE_LIMIT_WINDOW_SECONDS,
            error_code=ErrorCode.AI_PROVIDER_UNAVAILABLE,
            status_code=503,
        )

        success = False
        try:
            result = await func(*args)
            success = True
            return result
        except AIResponseError as exc:
            raise FlamesAPIError(
                502, ErrorCode.AI_PROVIDER_UNAVAILABLE, f"AI provider returned a bad result: {exc}"
            ) from exc
        except TimeoutError as exc:
            raise FlamesAPIError(
                504, ErrorCode.AI_PROVIDER_TIMEOUT, "AI provider request timed out"
            ) from exc
        finally:
            await self._usage_logs.create(
                AIUsageLog(
                    provider=self._provider_name,
                    model=self._model,
                    task_type=task_type,
                    tokens_used=None,
                    cost=None,
                    success=success,
                )
            )
            await self._db.commit()


def get_ai_service(db: AsyncSession) -> AIService:
    settings = get_settings()
    return AIService(
        db=db,
        provider=get_ai_provider(),
        usage_log_repository=AIUsageLogRepository(db),
        provider_name=settings.ai_provider,
        model=settings.groq_model if settings.ai_provider == "groq" else settings.deepseek_model,
        rate_limit_per_minute=settings.ai_rate_limit_per_minute,
    )
