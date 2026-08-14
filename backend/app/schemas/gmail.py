"""API-facing schemas for the Gmail OAuth flow."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class GmailConnectResponse(BaseModel):
    consent_url: str


class GmailStatusResponse(BaseModel):
    connected: bool
    last_synced_at: datetime | None
