"""Groq/DeepSeek calls are mocked at the HTTP boundary (Phase 2 §20) —
never a real call in the automated suite.
"""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from app.ai.base_provider import AIResponseError
from app.ai.groq_provider import GROQ_BASE_URL, GroqProvider
from flames_shared.dto import JobPosting
from flames_shared.enums import JobSourceType


def _job() -> JobPosting:
    return JobPosting(
        source=JobSourceType.REMOTEOK,
        external_id="123",
        title="Backend Engineer",
        company="Acme",
        url="https://example.com/job",
        description="Build things with Python.",
    )


def _chat_completion_response(content: str) -> dict:
    return {
        "id": "chatcmpl-test",
        "choices": [{"message": {"role": "assistant", "content": content}}],
    }


@respx.mock
async def test_score_match_parses_valid_json_response() -> None:
    payload = {"score": 88, "decision": "APPLY", "reasons": ["good fit"], "missing_skills": []}
    respx.post(f"{GROQ_BASE_URL}/chat/completions").mock(
        return_value=httpx.Response(200, json=_chat_completion_response(json.dumps(payload)))
    )

    provider = GroqProvider(api_key="test-key", model="test-model")
    result = await provider.score_match(_job(), cv_profile={"skills": ["python"]})

    assert result.score == 88
    assert result.decision == "APPLY"


@respx.mock
async def test_score_match_raises_on_malformed_json() -> None:
    respx.post(f"{GROQ_BASE_URL}/chat/completions").mock(
        return_value=httpx.Response(200, json=_chat_completion_response("not valid json"))
    )

    provider = GroqProvider(api_key="test-key", model="test-model")
    with pytest.raises(AIResponseError):
        await provider.score_match(_job(), cv_profile={})


@respx.mock
async def test_score_match_raises_on_schema_violation() -> None:
    # "score" out of the 0-100 range the MatchResult schema enforces.
    payload = {"score": 500, "decision": "APPLY", "reasons": [], "missing_skills": []}
    respx.post(f"{GROQ_BASE_URL}/chat/completions").mock(
        return_value=httpx.Response(200, json=_chat_completion_response(json.dumps(payload)))
    )

    provider = GroqProvider(api_key="test-key", model="test-model")
    with pytest.raises(AIResponseError):
        await provider.score_match(_job(), cv_profile={})
