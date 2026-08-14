"""Cross-module data contracts.

Every payload that crosses a module boundary (Search -> AI -> Application ->
Notification, etc.) is one of these types. Modules depend on these shapes,
never on each other's internal classes or ORM models.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from flames_shared.enums import (
    ApplicationStatus,
    EmailCategory,
    JobSourceType,
    NotificationLevel,
)


class JobPosting(BaseModel):
    """A job discovered by the Search Engine, before any AI analysis."""

    model_config = ConfigDict(frozen=True)

    source: JobSourceType
    external_id: str = Field(description="ID/slug unique within the source site")
    title: str
    company: str
    location: str | None = None
    url: str
    description: str
    posted_at: datetime | None = None
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    raw_metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def fingerprint(self) -> str:
        """Stable identity used for duplicate detection across sources."""
        return f"{self.source}:{self.external_id}"


class JobAnalysis(BaseModel):
    """AI Engine output for AIProvider.analyze_job() — structured
    requirements extracted from a raw job description."""

    required_skills: list[str] = Field(default_factory=list)
    seniority_level: str
    must_haves: list[str] = Field(default_factory=list)
    nice_to_haves: list[str] = Field(default_factory=list)
    summary: str


class MatchResult(BaseModel):
    """AI Engine output for AIProvider.score_match() (Part 6 §75).

    `decision` is the AI's raw suggestion (e.g. "APPLY"/"REVIEW"/"SKIP") —
    it is advisory only. The final routing decision combines this with
    job_rules and a risk check (Part 6 §76: "Application logic controls
    execution"), it never comes from the AI alone.
    """

    score: int = Field(ge=0, le=100)
    decision: str
    reasons: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)


class EmailClassificationResult(BaseModel):
    """AI Engine output for AIProvider.classify_email() (Part 6 §78)."""

    category: EmailCategory
    confidence: int = Field(ge=0, le=100)
    important: bool


class CoverLetterDraft(BaseModel):
    job_fingerprint: str
    content: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ApplicationRecord(BaseModel):
    """The audit trail entry for a single application attempt."""

    job_fingerprint: str
    status: ApplicationStatus
    method: str | None = None
    reason: str | None = None
    applied_at: datetime | None = None
    artifacts: dict[str, Any] = Field(default_factory=dict)


class EmailEvent(BaseModel):
    message_id: str
    sender: str
    subject: str
    received_at: datetime
    category: EmailCategory
    related_job_fingerprint: str | None = None
    snippet: str = ""


class NotificationPayload(BaseModel):
    title: str
    body: str
    level: NotificationLevel = NotificationLevel.INFO
    metadata: dict[str, Any] = Field(default_factory=dict)


class TelegramIntent(BaseModel):
    """AI Engine output for AIProvider.interpret_telegram_message() — maps
    a free-text Telegram message onto one of the bot's existing read-only
    commands, or a plain conversational reply if none applies.

    Advisory only, same as MatchResult (Part 6 §69): the AI never
    triggers a state-changing command (pause/resume, apply/skip) from
    free text, only read-only ones — `command` is validated against that
    allowlist by the caller regardless of what the model returns.
    """

    command: str | None = None
    reply: str
