"""Shared implementation for OpenAI-chat-completions-compatible AI
vendors (Groq, DeepSeek — both speak the same protocol). Concrete
subclasses (`groq_provider.py`, `deepseek_provider.py`) only construct the
right `AsyncOpenAI` client; the five `AIProvider` methods, prompt
rendering, and JSON-response validation live here once so they're never
duplicated per vendor.
"""

from __future__ import annotations

import json
import logging
from typing import TypeVar

from flames_shared.constants import MAX_JOB_DESCRIPTION_CHARS
from flames_shared.dto import (
    CoverLetterDraft,
    EmailClassificationResult,
    JobAnalysis,
    JobPosting,
    MatchResult,
    TelegramIntent,
)
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.ai.prompt_loader import render_prompt
from app.ai.provider import AIProvider

logger = logging.getLogger(__name__)

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class AIResponseError(Exception):
    """The model responded, but the response failed schema validation —
    a malformed/partial JSON result should raise, never silently return
    None fields to the caller (Phase 2 §14)."""


class _ChatCompletionAIProvider(AIProvider):
    def __init__(self, client: AsyncOpenAI, model: str) -> None:
        self._client = client
        self._model = model

    async def analyze_job(self, job: JobPosting) -> dict[str, object]:
        prompt = render_prompt(
            "job_analysis",
            job_title=job.title,
            company=job.company,
            description=job.description[:MAX_JOB_DESCRIPTION_CHARS],
        )
        analysis = await self._json_completion(prompt, JobAnalysis)
        return analysis.model_dump()

    async def score_match(self, job: JobPosting, cv_profile: dict[str, object]) -> MatchResult:
        prompt = render_prompt(
            "job_matching",
            job_title=job.title,
            company=job.company,
            description=job.description[:MAX_JOB_DESCRIPTION_CHARS],
            cv_text=_cv_profile_to_text(cv_profile),
        )
        return await self._json_completion(prompt, MatchResult)

    async def generate_cover_letter(
        self, job: JobPosting, cv_profile: dict[str, object]
    ) -> CoverLetterDraft:
        prompt = render_prompt(
            "cover_letter",
            job_title=job.title,
            company=job.company,
            description=job.description[:MAX_JOB_DESCRIPTION_CHARS],
            cv_text=_cv_profile_to_text(cv_profile),
        )
        content = await self._text_completion(prompt)
        return CoverLetterDraft(job_fingerprint=job.fingerprint, content=content)

    async def classify_email(self, email_content: str) -> EmailClassificationResult:
        prompt = render_prompt("email_classifier", email_content=email_content)
        return await self._json_completion(prompt, EmailClassificationResult)

    async def answer_question(self, question: str, cv_profile: dict[str, object]) -> str:
        prompt = render_prompt(
            "application_answers", question=question, context=_cv_profile_to_text(cv_profile)
        )
        return await self._text_completion(prompt)

    async def interpret_telegram_message(
        self, message: str, available_commands: dict[str, str]
    ) -> TelegramIntent:
        command_list = "\n".join(f"- {name}: {desc}" for name, desc in available_commands.items())
        prompt = render_prompt("telegram_assistant", command_list=command_list, message=message)
        return await self._json_completion(prompt, TelegramIntent)

    async def _text_completion(self, prompt: str) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.choices[0].message.content
        if not content:
            raise AIResponseError("Empty response from AI provider")
        return content.strip()

    async def _json_completion(self, prompt: str, schema: type[SchemaT]) -> SchemaT:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        if not content:
            raise AIResponseError("Empty response from AI provider")
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise AIResponseError(f"AI provider returned invalid JSON: {exc}") from exc
        try:
            return schema.model_validate(data)
        except Exception as exc:  # pydantic.ValidationError, kept broad deliberately
            raise AIResponseError(f"AI provider response failed validation: {exc}") from exc


def _cv_profile_to_text(cv_profile: dict[str, object]) -> str:
    if not cv_profile:
        return "(no profile data provided)"
    return "\n".join(f"{key}: {value}" for key, value in cv_profile.items())
