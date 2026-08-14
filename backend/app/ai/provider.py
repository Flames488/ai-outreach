"""Provider-agnostic AI interface (Part 6 §70: `AIProvider -> Groq`).

Every AI capability Flames needs is defined here; concrete providers
(Groq today, anything else tomorrow) implement this contract so calling
code never depends on a specific vendor. Only Groq ships in v1 — adding a
second provider is a new class here plus a config change, never a rewrite
of `app/services/ai_service.py`.

AI advises, it doesn't act unilaterally (§69) — every method here returns
a recommendation or a draft; nothing here submits an application or sends
a message on its own.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from flames_shared.dto import (
    CoverLetterDraft,
    EmailClassificationResult,
    JobPosting,
    MatchResult,
    TelegramIntent,
)


class AIProvider(ABC):
    @abstractmethod
    async def analyze_job(self, job: JobPosting) -> dict[str, object]:
        """Extract structured requirements (required skills, seniority,
        must-haves) from a raw job description — AITaskType.JOB_ANALYSIS."""

    @abstractmethod
    async def score_match(self, job: JobPosting, cv_profile: dict[str, object]) -> MatchResult:
        """Score how well a job matches the candidate's CV profile —
        AITaskType.JOB_MATCHING. See §75/§76: this is advisory, combined
        with job_rules downstream, never applied directly."""

    @abstractmethod
    async def generate_cover_letter(
        self, job: JobPosting, cv_profile: dict[str, object]
    ) -> CoverLetterDraft:
        """Draft a tailored cover letter for a job above the relevance
        threshold — AITaskType.COVER_LETTER. No fabricated experience,
        max 500 words, professional tone (§77)."""

    @abstractmethod
    async def classify_email(self, email_content: str) -> EmailClassificationResult:
        """Classify a recruiter email — AITaskType.EMAIL_CLASSIFICATION."""

    @abstractmethod
    async def answer_question(self, question: str, cv_profile: dict[str, object]) -> str:
        """Answer a free-text application form question using the CV
        profile — AITaskType.APPLICATION_ANSWER."""

    @abstractmethod
    async def interpret_telegram_message(
        self, message: str, available_commands: dict[str, str]
    ) -> TelegramIntent:
        """Map a free-text Telegram message onto one of the bot's existing
        commands, or produce a direct conversational reply —
        AITaskType.TELEGRAM_ASSISTANT. Advisory only: the caller still
        validates `command` against the allowlist it passed in."""
