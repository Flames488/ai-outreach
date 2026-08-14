"""Inline keyboard builders (Phase 2 §16's Job Review flow).

`job_id` (a UUID string, 36 chars) fits well inside Telegram's 64-byte
`callback_data` limit alongside a short action prefix, so no Redis-backed
token indirection is needed for this one.
"""

from __future__ import annotations

from typing import Any


def job_review_keyboard(job_id: str) -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "Apply", "callback_data": f"job:apply:{job_id}"},
                {"text": "Skip", "callback_data": f"job:skip:{job_id}"},
                {"text": "View Details", "callback_data": f"job:view:{job_id}"},
            ]
        ]
    }
