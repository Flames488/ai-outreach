"""Central application configuration, loaded once from environment variables.

Every credential and tunable lives here — grep the codebase for
`os.getenv`/`os.environ` outside this file; any hit is a standards
violation (Phase 2 §08).

Two tiers of "required":

- Infra secrets (SECRET_KEY, JWT_SECRET, POSTGRES_PASSWORD,
  MASTER_ENCRYPTION_KEY) cost nothing to generate locally (no external
  account needed) — boot fails immediately if any is blank.
- Integration credentials (Groq, Telegram, Google) require an external
  account the user may not have set up yet. Phase 2's spec says these
  should be hard-required too ("the crash is the point") — kept soft
  here instead (blank allowed, `warn_on_missing_integration_credentials()`
  logs a warning at API startup) so the infra stack is testable before
  those accounts exist. Revisit once real credentials are available.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_REQUIRED_INFRA_SECRETS = (
    "secret_key",
    "jwt_secret",
    "postgres_password",
    "master_encryption_key",
)
_INTEGRATION_CREDENTIALS = (
    "telegram_bot_token",
    "telegram_chat_id",
    "telegram_webhook_secret",
    "google_client_id",
    "google_client_secret",
    "google_redirect_uri",
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- Project ----
    app_name: str = Field(default="Flames", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=True, alias="DEBUG")
    secret_key: str = Field(default="", alias="SECRET_KEY")
    jwt_secret: str = Field(default="", alias="JWT_SECRET")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = Field(default=1440, alias="JWT_EXPIRE_MINUTES")
    # Comma-separated. "*" (dev default) disables TrustedHostMiddleware's
    # allowlist; set a real list of hostnames in production.
    allowed_hosts: str = Field(default="*", alias="ALLOWED_HOSTS")
    # Comma-separated. "*" (dev default) — CORSMiddleware silently ignores
    # allow_credentials with a literal wildcard origin per spec, which is
    # fine in dev (this API is Bearer-token, not cookie, auth), but set a
    # real origin (the dashboard's own) in production instead of relying
    # on that.
    cors_allowed_origins: str = Field(default="*", alias="CORS_ALLOWED_ORIGINS")
    # Where the dashboard is served — used only to redirect the browser
    # back there after the Gmail OAuth consent flow. Left blank, that
    # callback falls back to returning its JSON envelope directly rather
    # than guessing a URL.
    frontend_url: str = Field(default="", alias="FRONTEND_URL")

    # ---- Database ----
    postgres_db: str = Field(default="flames", alias="POSTGRES_DB")
    postgres_user: str = Field(default="postgres", alias="POSTGRES_USER")
    postgres_password: str = Field(default="", alias="POSTGRES_PASSWORD")
    database_url: str = Field(default="", alias="DATABASE_URL")

    # ---- Redis ----
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")

    # ---- Telegram ----
    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field(default="", alias="TELEGRAM_CHAT_ID")
    telegram_webhook_secret: str = Field(default="", alias="TELEGRAM_WEBHOOK_SECRET")

    # ---- AI provider selection ----
    # "groq" (default, per Phase 2 spec) or "deepseek" (per ROADMAP.md's
    # "DeepSeek support" goal) — both speak the OpenAI chat-completions
    # protocol, selected here so swapping is a config change, never a
    # rewrite of app/services/ai_service.py.
    ai_provider: str = Field(default="groq", alias="AI_PROVIDER")
    ai_rate_limit_per_minute: int = Field(default=25, alias="AI_RATE_LIMIT_PER_MINUTE")

    # ---- Groq ----
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.3-70b-versatile", alias="GROQ_MODEL")

    # ---- DeepSeek ----
    deepseek_api_key: str = Field(default="", alias="DEEPSEEK_API_KEY")
    deepseek_model: str = Field(default="deepseek-chat", alias="DEEPSEEK_MODEL")

    # ---- Gmail / Google OAuth ----
    google_client_id: str = Field(default="", alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(default="", alias="GOOGLE_CLIENT_SECRET")
    google_refresh_token: str = Field(default="", alias="GOOGLE_REFRESH_TOKEN")
    google_redirect_uri: str = Field(default="", alias="GOOGLE_REDIRECT_URI")
    google_project_id: str = Field(default="", alias="GOOGLE_PROJECT_ID")
    gmail_address: str = Field(default="", alias="GMAIL_ADDRESS")
    gmail_sync_interval: int = Field(default=300, alias="GMAIL_SYNC_INTERVAL")
    enable_attachment_download: bool = Field(default=False, alias="ENABLE_ATTACHMENT_DOWNLOAD")
    max_attachment_size_mb: int = Field(default=25, alias="MAX_ATTACHMENT_SIZE_MB")

    # ---- Encryption ----
    master_encryption_key: str = Field(default="", alias="MASTER_ENCRYPTION_KEY")

    # ---- Seed (scripts/seed.py only — never used by ongoing login) ----
    seed_admin_email: str = Field(default="admin@flames.local", alias="SEED_ADMIN_EMAIL")
    seed_admin_password: str = Field(default="", alias="SEED_ADMIN_PASSWORD")

    # ---- Job search & scheduler behavior ----
    job_search_time_morning: str = Field(default="07:00", alias="JOB_SEARCH_TIME_MORNING")
    job_search_time_afternoon: str = Field(default="12:00", alias="JOB_SEARCH_TIME_AFTERNOON")
    job_search_time_evening: str = Field(default="19:00", alias="JOB_SEARCH_TIME_EVENING")
    # Not in the Phase 2 .env.example (only the two search times and the
    # Gmail interval are called out there) — kept configurable anyway per
    # the general "schedule times aren't hardcoded" rule, default matches
    # the spec's fixed 00:00.
    cleanup_time: str = Field(default="00:00", alias="CLEANUP_TIME")
    job_search_max_results: int = Field(default=200, alias="JOB_SEARCH_MAX_RESULTS")
    job_match_threshold: int = Field(default=80, ge=0, le=100, alias="JOB_MATCH_THRESHOLD")

    # ---- Google Jobs (via SerpApi — Google has no free public jobs API) ----
    serpapi_key: str = Field(default="", alias="SERPAPI_KEY")
    google_jobs_query: str = Field(
        default="web developer OR full stack developer OR AI automation",
        alias="GOOGLE_JOBS_QUERY",
    )
    google_jobs_location: str = Field(default="Remote", alias="GOOGLE_JOBS_LOCATION")

    # ---- Greenhouse / Lever (per-company job boards — no generic search;
    # comma-separated board tokens, the slug in boards.greenhouse.io/<token>
    # or jobs.lever.co/<token>) ----
    greenhouse_companies: str = Field(
        default="gitlab,stripe,coinbase,airbnb", alias="GREENHOUSE_COMPANIES"
    )
    lever_companies: str = Field(default="palantir,plaid,lever", alias="LEVER_COMPANIES")

    # ---- Storage (consolidated) ----
    storage_root: str = Field(default="/app/storage", alias="STORAGE_ROOT")
    log_dir: str = Field(default="/app/logs", alias="LOG_DIR")

    # ---- Playwright (Phase 3: dry-run application engine) ----
    playwright_headless: bool = Field(default=True, alias="PLAYWRIGHT_HEADLESS")
    playwright_timeout: int = Field(default=30000, alias="PLAYWRIGHT_TIMEOUT_MS")
    playwright_slowmo: int = Field(default=0, alias="PLAYWRIGHT_SLOWMO_MS")
    playwright_screenshot_dir: str = Field(
        default="/app/storage/screenshots", alias="PLAYWRIGHT_SCREENSHOT_DIR"
    )

    # ---- Feature flags ----
    enable_playwright: bool = Field(default=False, alias="ENABLE_PLAYWRIGHT")
    enable_gmail: bool = Field(default=True, alias="ENABLE_GMAIL")
    enable_telegram: bool = Field(default=True, alias="ENABLE_TELEGRAM")
    enable_ai_scoring: bool = Field(default=True, alias="ENABLE_AI_SCORING")
    enable_auto_apply: bool = Field(default=False, alias="ENABLE_AUTO_APPLY")
    enable_dashboard: bool = Field(default=False, alias="ENABLE_DASHBOARD")
    enable_screenshots: bool = Field(default=False, alias="ENABLE_SCREENSHOTS")
    enable_resume_generator: bool = Field(default=False, alias="ENABLE_RESUME_GENERATOR")
    enable_interview_preparation: bool = Field(default=False, alias="ENABLE_INTERVIEW_PREPARATION")

    # ---- Celery / monitoring ----
    flower_port: int = Field(default=5555, alias="FLOWER_PORT")

    @model_validator(mode="after")
    def _derive_database_url(self) -> Settings:
        if not self.database_url:
            self.database_url = (
                f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
                f"@postgres:5432/{self.postgres_db}"
            )
        return self

    @model_validator(mode="after")
    def _fail_fast_on_missing_infra_secrets(self) -> Settings:
        missing = [name for name in _REQUIRED_INFRA_SECRETS if not getattr(self, name)]
        if missing:
            env_names = ", ".join(name.upper() for name in missing)
            raise ValueError(
                f"Missing required environment variable(s): {env_names}. "
                "Set them in .env before starting Flames."
            )
        return self

    @model_validator(mode="after")
    def _validate_master_encryption_key(self) -> Settings:
        if not self.master_encryption_key:
            return self  # already caught by _fail_fast_on_missing_infra_secrets
        from cryptography.fernet import Fernet

        try:
            Fernet(self.master_encryption_key.encode("utf-8"))
        except (ValueError, TypeError) as exc:
            raise ValueError(
                "MASTER_ENCRYPTION_KEY is not a valid Fernet key. Generate one with: "
                'python -c "from cryptography.fernet import Fernet; '
                'print(Fernet.generate_key().decode())"'
            ) from exc
        return self

    @property
    def allowed_hosts_list(self) -> list[str]:
        return [host.strip() for host in self.allowed_hosts.split(",") if host.strip()]

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        origins = self.cors_allowed_origins.split(",")
        return [origin.strip() for origin in origins if origin.strip()]

    @property
    def greenhouse_companies_list(self) -> list[str]:
        return [c.strip() for c in self.greenhouse_companies.split(",") if c.strip()]

    @property
    def lever_companies_list(self) -> list[str]:
        return [c.strip() for c in self.lever_companies.split(",") if c.strip()]

    @property
    def celery_broker_url(self) -> str:
        return _with_redis_db(self.redis_url, 1)

    @property
    def celery_result_backend(self) -> str:
        return _with_redis_db(self.redis_url, 2)

    def hour_minute(self, time_str: str) -> tuple[int, int]:
        hour_str, minute_str = time_str.split(":")
        return int(hour_str), int(minute_str)

    def warn_on_missing_integration_credentials(self) -> None:
        active_ai_key = "deepseek_api_key" if self.ai_provider == "deepseek" else "groq_api_key"
        missing = [
            name for name in (*_INTEGRATION_CREDENTIALS, active_ai_key) if not getattr(self, name)
        ]
        for name in missing:
            logger.warning(
                "%s is not set — the feature that depends on it will be unavailable "
                "until it's configured in .env.",
                name.upper(),
            )


def _with_redis_db(redis_url: str, db_index: int) -> str:
    base, _, _ = redis_url.rpartition("/")
    return f"{base}/{db_index}" if base else redis_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
