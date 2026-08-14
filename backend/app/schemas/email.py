"""API-facing read model for emails."""

from __future__ import annotations

import uuid
from datetime import datetime

from flames_shared.enums import EmailCategory
from pydantic import BaseModel, ConfigDict


class EmailRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sender: str
    recipient: str | None
    subject: str
    snippet: str
    received_at: datetime
    category: EmailCategory
    processed: bool
