"""Loads AI prompt templates from `backend/prompts/*.md` and fills
`{{variable}}` placeholders (Phase 2 §14 / Part 6 §80) — prompts are
never hardcoded Python string literals, so they can be iterated and
version-controlled without a code change.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"

_PLACEHOLDER_RE = re.compile(r"\{\{(\w+)\}\}")


class PromptNotFoundError(Exception):
    pass


@lru_cache
def _load_raw(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.md"
    if not path.is_file():
        raise PromptNotFoundError(f"No prompt file at {path}")
    return path.read_text(encoding="utf-8")


def render_prompt(name: str, **variables: object) -> str:
    template = _load_raw(name)

    def _replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in variables:
            raise KeyError(f"Prompt '{name}' references undefined variable '{{{{{key}}}}}'")
        return str(variables[key])

    return _PLACEHOLDER_RE.sub(_replace, template)
