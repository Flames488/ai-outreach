"""Import every model so Base.metadata is complete for Alembic autogenerate."""

from app.database.base import Base
from app.models.ai_usage_log import AIUsageLog
from app.models.application import Application
from app.models.application_rule import ApplicationRule
from app.models.audit_log import AuditLog
from app.models.company import Company
from app.models.cover_letter import CoverLetter
from app.models.cv_version import CVVersion
from app.models.email_label import EmailLabel
from app.models.email_message import EmailMessage
from app.models.feature_flag import FeatureFlag
from app.models.job import Job
from app.models.job_skill import JobSkill
from app.models.notification import Notification
from app.models.provider_log import ProviderLog
from app.models.refresh_token import RefreshToken
from app.models.saved_answer import SavedAnswer
from app.models.scheduled_task import ScheduledTask
from app.models.system_log import SystemLog
from app.models.task_log import TaskLog
from app.models.telegram_message import TelegramMessage
from app.models.user import User
from app.models.user_profile import UserProfile

__all__ = [
    "AIUsageLog",
    "Application",
    "ApplicationRule",
    "AuditLog",
    "Base",
    "Company",
    "CoverLetter",
    "CVVersion",
    "EmailLabel",
    "EmailMessage",
    "FeatureFlag",
    "Job",
    "JobSkill",
    "Notification",
    "ProviderLog",
    "RefreshToken",
    "SavedAnswer",
    "ScheduledTask",
    "SystemLog",
    "TaskLog",
    "TelegramMessage",
    "User",
    "UserProfile",
]
