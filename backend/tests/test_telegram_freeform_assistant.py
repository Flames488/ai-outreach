"""Free-text Telegram assistant routing (Phase 5) — verifies intent
mapping stays inside the read-only allowlist and that AI failures degrade
to a plain-text fallback instead of raising into the webhook route.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.telegram.handlers import dispatch_freeform_message
from flames_shared.dto import TelegramIntent
from flames_shared.enums import UserRole


def _user(role: UserRole = UserRole.USER) -> SimpleNamespace:
    return SimpleNamespace(id="user-1", email="user@example.com", role=role, gmail_connected=False)


async def test_routes_to_matched_command_with_ai_lead_in() -> None:
    fake_service = SimpleNamespace(
        interpret_telegram_message=AsyncMock(
            return_value=TelegramIntent(command="stats", reply="Here you go.")
        )
    )
    fake_dashboard = SimpleNamespace(
        get_summary=AsyncMock(
            return_value=SimpleNamespace(
                total_jobs=1,
                matched_jobs=1,
                pending_review=0,
                total_applications=0,
                queued_applications=0,
                unprocessed_emails=0,
            )
        )
    )
    with (
        patch("app.telegram.handlers.get_ai_service", return_value=fake_service),
        patch("app.telegram.handlers.get_dashboard_service", return_value=fake_dashboard),
    ):
        result = await dispatch_freeform_message(db=object(), user=_user(), text="how's it going?")

    assert len(result) == 1
    text, markup = result[0]
    assert text.startswith("Here you go.")
    assert "Total jobs: 1" in text
    assert markup is None


async def test_falls_back_to_reply_when_no_command_matches() -> None:
    fake_service = SimpleNamespace(
        interpret_telegram_message=AsyncMock(
            return_value=TelegramIntent(command=None, reply="I can help with that — try /help.")
        )
    )
    with patch("app.telegram.handlers.get_ai_service", return_value=fake_service):
        result = await dispatch_freeform_message(db=object(), user=_user(), text="hello")

    assert result == [("I can help with that — try /help.", None)]


async def test_ignores_state_changing_command_even_if_ai_suggests_it() -> None:
    """The AI can never trigger /pause or /resume from free text — only
    the explicit slash command may (see ASSISTANT_ELIGIBLE_COMMANDS)."""
    fake_service = SimpleNamespace(
        interpret_telegram_message=AsyncMock(
            return_value=TelegramIntent(command="pause", reply="Pausing everything now.")
        )
    )
    with patch("app.telegram.handlers.get_ai_service", return_value=fake_service):
        result = await dispatch_freeform_message(db=object(), user=_user(), text="stop everything")

    # command is rejected as out-of-allowlist, so only the reply is sent —
    # the pause handler never runs.
    assert result == [("Pausing everything now.", None)]


async def test_degrades_gracefully_on_ai_failure() -> None:
    fake_service = SimpleNamespace(
        interpret_telegram_message=AsyncMock(side_effect=RuntimeError("provider unavailable"))
    )
    with patch("app.telegram.handlers.get_ai_service", return_value=fake_service):
        result = await dispatch_freeform_message(db=object(), user=_user(), text="anything")

    assert len(result) == 1
    assert "couldn't process" in result[0][0].lower()


async def test_admin_only_commands_excluded_for_regular_users() -> None:
    fake_service = SimpleNamespace(interpret_telegram_message=AsyncMock())
    with patch("app.telegram.handlers.get_ai_service", return_value=fake_service):
        await dispatch_freeform_message(db=object(), user=_user(UserRole.USER), text="show logs")

    available_commands = fake_service.interpret_telegram_message.call_args.args[1]
    assert "logs" not in available_commands
    assert "health" not in available_commands
