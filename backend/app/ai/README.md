# AI

Job analysis, match scoring, cover letter generation, email
classification, and application Q&A — concrete AI vendor implementations
live here. `app/services/ai_service.py` is what the rest of the app
actually calls; it rate-limits and logs every call to `ai_usage_logs`.

- `provider.py` — `AIProvider` ABC: `analyze_job`, `score_match`,
  `generate_cover_letter`, `classify_email`, `answer_question`
- `base_provider.py` — `_ChatCompletionAIProvider`: shared implementation
  against any OpenAI-chat-completions-compatible vendor (prompt
  rendering, JSON-mode parsing + Pydantic validation, text completions)
- `groq_provider.py` / `deepseek_provider.py` — thin subclasses that only
  construct the right `AsyncOpenAI` client (base URL, API key, model)
- `registry.py` — `get_ai_provider()`, selects Groq vs. DeepSeek from
  `AI_PROVIDER` — the only place that decision is made
- `prompt_loader.py` — loads `backend/prompts/*.md`, fills `{{var}}` placeholders

## Status

Fully implemented against both vendors — real HTTP calls, JSON-mode
responses validated against `flames_shared.dto.{JobAnalysis,MatchResult,
EmailClassificationResult}` immediately after parsing (raises
`AIResponseError`, not silently-`None` fields, on a malformed response).

Groq is the default (`AI_PROVIDER=groq`); DeepSeek support was added
because the active build goal (`ROADMAP.md`) calls for it, superseding an
earlier "Groq only" decision from the detailed Phase 1/2 specs.

## Swapping / adding providers

Implement a new `_ChatCompletionAIProvider` subclass (if it's OpenAI-chat-
completions-compatible — most are) or a fresh `AIProvider` subclass
otherwise, then add one branch in `registry.get_ai_provider()`. No other
module imports a concrete provider class directly.

## AI never acts unilaterally

`score_match()` returns an advisory `MatchResult` (score + a suggested
`decision`) — the actual apply/review/skip routing combines this with
`application_rules` (see `app/rules/`) and a risk check in the calling
service, never the AI alone.
