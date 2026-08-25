"""Google OAuth 2.0 flow for Gmail (Phase 2 §15). Scopes are read-only —
Flames only ever reads the inbox, never sends or modifies mail.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import cast

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from jose import JWTError, jwt

from app.config.settings import get_settings

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.labels",
]

_STATE_EXPIRE_MINUTES = 10


def _build_flow(code_verifier: str | None = None) -> Flow:
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
        client_config,
        scopes=GMAIL_SCOPES,
        redirect_uri=settings.google_redirect_uri,
        code_verifier=code_verifier,
    )


def _encode_state(user_id: str, code_verifier: str) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "code_verifier": code_verifier,
        "type": "gmail_oauth_state",
        "iat": now,
        "exp": now + timedelta(minutes=_STATE_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_state(state: str) -> tuple[str, str] | None:
    """Returns (user_id, code_verifier), or None if state is missing,
    expired, or tampered with."""
    settings = get_settings()
    try:
        payload = jwt.decode(state, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
    if payload.get("type") != "gmail_oauth_state":
        return None
    user_id = payload.get("sub")
    code_verifier = payload.get("code_verifier")
    if not isinstance(user_id, str) or not isinstance(code_verifier, str):
        return None
    return user_id, code_verifier


def build_consent_url(user_id: str) -> str:
    """`state` round-trips through Google unchanged and is how
    `/gmail/callback` — a plain browser redirect Google makes, which can
    never carry an Authorization header — knows which user is connecting
    (see app/api/v1/gmail.py). It also carries the PKCE code_verifier:
    `/connect` and `/callback` build separate `Flow` instances (different
    HTTP requests, possibly different worker processes), so the verifier
    a freshly-built `Flow` would auto-generate on its own is never the
    one Google actually issued a code_challenge against. Generating it
    ourselves and threading it through state is what makes the two ends
    agree."""
    code_verifier = secrets.token_urlsafe(96)
    flow = _build_flow(code_verifier=code_verifier)
    url, _state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
        state=_encode_state(user_id, code_verifier),
    )
    return cast(str, url)


def exchange_code_for_credentials(code: str, code_verifier: str) -> Credentials:
    flow = _build_flow(code_verifier=code_verifier)
    flow.fetch_token(code=code)
    return cast(Credentials, flow.credentials)
