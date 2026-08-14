"""Composition root for AIProvider selection (Phase 2 §14). This is the
only place that picks Groq vs. DeepSeek — swapping providers, or adding a
third, is a change here plus `AI_PROVIDER` in `.env`, never a rewrite of
`app/services/ai_service.py` or anything that calls it.
"""

from __future__ import annotations

from app.ai.provider import AIProvider
from app.config.settings import get_settings


def get_ai_provider() -> AIProvider:
    settings = get_settings()
    if settings.ai_provider == "deepseek":
        from app.ai.deepseek_provider import DeepSeekProvider

        return DeepSeekProvider()

    from app.ai.groq_provider import GroqProvider

    return GroqProvider()
