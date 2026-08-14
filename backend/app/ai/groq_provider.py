"""Groq-backed AIProvider — Groq exposes an OpenAI-compatible chat
completions endpoint, so this only wires the client; behavior lives in
`base_provider._ChatCompletionAIProvider`.
"""

from __future__ import annotations

from openai import AsyncOpenAI

from app.ai.base_provider import _ChatCompletionAIProvider
from app.config.settings import get_settings

GROQ_BASE_URL = "https://api.groq.com/openai/v1"


class GroqProvider(_ChatCompletionAIProvider):
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        settings = get_settings()
        client = AsyncOpenAI(api_key=api_key or settings.groq_api_key, base_url=GROQ_BASE_URL)
        super().__init__(client=client, model=model or settings.groq_model)
