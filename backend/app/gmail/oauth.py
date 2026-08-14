"""Google OAuth 2.0 flow for Gmail (Phase 2 §15). Scopes are read-only —
Flames only ever reads the inbox, never sends or modifies mail.
"""

from __future__ import annotations

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from app.config.settings import get_settings

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.labels",
]


def _build_flow() -> Flow:
    settings = get_settings()
    client_config = {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_redirect_uri],
        }
    }
    return Flow.from_client_config(
        client_config, scopes=GMAIL_SCOPES, redirect_uri=settings.google_redirect_uri
    )


def build_consent_url() -> str:
    flow = _build_flow()
    url, _state = flow.authorization_url(
        access_type="offline", prompt="consent", include_granted_scopes="true"
    )
    return url


def exchange_code_for_credentials(code: str) -> Credentials:
    flow = _build_flow()
    flow.fetch_token(code=code)
    return flow.credentials
