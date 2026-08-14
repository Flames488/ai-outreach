"""DeepSeek-backed AIProvider (ROADMAP.md's "DeepSeek support" goal —
Phase 1/2's detailed specs called for Groq only; the active session goal
supersedes that for this build). DeepSeek exposes an OpenAI-compatible
chat completions endpoint, so this only wires the client; behavior lives
in `base_provider._ChatCompletionAIProvider`.
"""

from __future__ import annotations

from openai import AsyncOpenAI

from app.ai.base_provider import _ChatCompletionAIProvider
from app.config.settings import get_settings

DEEPSEEK_BASE_URL = "https://api.deepseek.com"


class DeepSeekProvider(_ChatCompletionAIProvider):
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        settings = get_settings()
        client = AsyncOpenAI(
            api_key=api_key or settings.deepseek_api_key, base_url=DEEPSEEK_BASE_URL
        )
        super().__init__(client=client, model=model or settings.deepseek_model)
