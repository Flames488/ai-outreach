"""Shared enumerations used across all Flames services.

These are the vocabulary every module agrees on. A module should never
invent its own status/category enum for a concept already defined here.

Phase 2 reconciliation (see Phase 2 `00-README.md`, "Source of truth for
schema decisions" — these values supersede Phase 1's originals):

- `ApplicationStatus` gains `QUEUED` (replacing `PENDING`) and
  `PENDING_VERIFICATION`; drops `APPLIED`/`SKIPPED`/`CANCELLED` stays.
- `EmailCategory` is the full Phase 2 canonical set (`JOB_OFFER`,
  `TECHNICAL_TEST`, `AUTO_REPLY`, `NEWSLETTER` replace the earlier
  `OFFER`/`GENERAL` pairing).
- `application_rules` (replacing `job_rules`) uses a JSONB
  field/op/value condition instead of a typed `rule_type` enum — so
  `JobRuleType` from Phase 1 is retired; `RuleOperator`/`RulePriorityTier`
  replace it.
"""

from __future__ import annotations

from enum import StrEnum


class JobStatus(StrEnum):
    """`jobs.status`. Maps onto the "Human Review Queue" lanes:
    MATCHED = auto-apply candidate, REVIEW = review required,
    SKIPPED = skip."""

    NEW = "new"
    MATCHED = "matched"
    REVIEW = "review"
    APPLIED = "applied"
    FAILED = "failed"
    SKIPPED = "skipped"
    EXPIRED = "expired"


class ApplicationStatus(StrEnum):
    """`applications.application_status`. Independent from JobStatus: a
    job only gets an Application row once it's actually queued."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    REVIEW_REQUIRED = "review_required"
    PENDING_VERIFICATION = "pending_verification"
    CANCELLED = "cancelled"


class JobSourceType(StrEnum):
    """Used by the provider-facing DTOs (flames_shared.dto.JobPosting,
    providers/mapping.py) — NOT the `jobs.provider` DB column, which is a
    plain string so new providers never need a migration."""

    LINKEDIN = "linkedin"
    INDEED = "indeed"
    GOOGLE_JOBS = "google_jobs"
    REMOTEOK = "remoteok"
    WELLFOUND = "wellfound"
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    COMPANY_SITE = "company_site"
    OTHER = "other"


class EmailCategory(StrEnum):
    """`email_messages.category` — Phase 2 canonical set."""

    INTERVIEW = "interview"
    JOB_OFFER = "job_offer"
    ASSESSMENT = "assessment"
    TECHNICAL_TEST = "technical_test"
    FOLLOW_UP = "follow_up"
    REJECTION = "rejection"
    AUTO_REPLY = "auto_reply"
    NEWSLETTER = "newsletter"
    UNKNOWN = "unknown"


class NotificationLevel(StrEnum):
    """Severity of an outbound notification payload (flames_shared.dto.
    NotificationPayload) — distinct from NotificationChannel below, which
    is which system delivered it."""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    SYSTEM = "system"


class NotificationChannel(StrEnum):
    """`notifications.channel`."""

    TELEGRAM = "telegram"
    EMAIL = "email"
    DASHBOARD = "dashboard"


class UserRole(StrEnum):
    """`users.role`. Future: TEAM_ADMIN, RECRUITER, VIEWER."""

    ADMIN = "admin"
    USER = "user"


class AITaskType(StrEnum):
    """`ai_usage_logs.task_type`."""

    JOB_ANALYSIS = "job_analysis"
    JOB_MATCHING = "job_matching"
    COVER_LETTER = "cover_letter"
    CV_IMPROVEMENT = "cv_improvement"
    EMAIL_CLASSIFICATION = "email_classification"
    APPLICATION_ANSWER = "application_answer"
    INTERVIEW_PREPARATION = "interview_preparation"
    TELEGRAM_ASSISTANT = "telegram_assistant"


class RulePriorityTier(StrEnum):
    """`application_rules.priority_tier`. Critical/Required are pass/fail
    gates evaluated in order; Preference only contributes to ranking."""

    CRITICAL = "critical"
    REQUIRED = "required"
    PREFERENCE = "preference"


class RuleOperator(StrEnum):
    """Allowed `condition.op` values on `application_rules` — the Rule
    Engine never `eval()`s an expression, only matches one of these."""

    EQ = "=="
    NE = "!="
    GTE = ">="
    LTE = "<="
    GT = ">"
    LT = "<"
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"


class TelegramDirection(StrEnum):
    """`telegram_messages.direction`."""

    INBOUND = "inbound"
    OUTBOUND = "outbound"


class ErrorCode(StrEnum):
    """Standardized API error codes. Every failure envelope
    (`app/schemas/envelope.py`) carries one of these, never a raw
    exception message or stack trace."""

    AUTH_INVALID_TOKEN = "AUTH_INVALID_TOKEN"
    AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
    AUTH_EXPIRED = "AUTH_EXPIRED"
    AUTH_FORBIDDEN = "AUTH_FORBIDDEN"
    DATABASE_ERROR = "DATABASE_ERROR"
    AI_PROVIDER_TIMEOUT = "AI_PROVIDER_TIMEOUT"
    AI_PROVIDER_UNAVAILABLE = "AI_PROVIDER_UNAVAILABLE"
    JOB_NOT_FOUND = "JOB_NOT_FOUND"
    APPLICATION_FAILED = "APPLICATION_FAILED"
    PLAYWRIGHT_TIMEOUT = "PLAYWRIGHT_TIMEOUT"
    GMAIL_AUTH_FAILED = "GMAIL_AUTH_FAILED"
    TELEGRAM_SEND_FAILED = "TELEGRAM_SEND_FAILED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    NOT_READY = "NOT_READY"
    INTERNAL_ERROR = "INTERNAL_ERROR"
