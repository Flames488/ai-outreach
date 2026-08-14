"""Unit tests for the Workday ATS plugin's dry-run flow (Phase 3) — a
fully mocked Page, no real browser needed. Real-browser coverage lives in
the manual smoke test (`scripts/dry_run_greenhouse.py`, which accepts any
registered plugin's URL) run against a live posting.

Workday's flow is multi-step and click-driven (Apply -> Autofill with
Resume -> Create Account), unlike Greenhouse/Lever's single-page forms —
these tests exercise that click sequence, not just field-filling."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from app.playwright.plugins.workday import WorkdayPlugin


def _locator(*, count: int = 1, enabled: bool = True) -> MagicMock:
    locator = MagicMock()
    locator.count = AsyncMock(return_value=count)
    locator.wait_for = AsyncMock()
    locator.click = AsyncMock()
    locator.check = AsyncMock()
    locator.is_enabled = AsyncMock(return_value=enabled)
    first = MagicMock()
    first.wait_for = AsyncMock()
    first.click = AsyncMock()
    first.is_enabled = AsyncMock(return_value=enabled)
    locator.first = first
    return locator


def _page(
    *,
    email_signin_button_present: bool = True,
    checkbox_count: int = 1,
    submit_enabled: bool = True,
) -> MagicMock:
    page = MagicMock()
    page.wait_for_selector = AsyncMock()
    page.fill = AsyncMock()

    email_signin_locator = _locator()
    if not email_signin_button_present:
        email_signin_locator.wait_for = AsyncMock(side_effect=TimeoutError("not present"))

    locators = {
        '[data-automation-id="legalNoticeAcceptButton"]': _locator(),
        '[data-automation-id="adventureButton"]': _locator(),
        '[data-automation-id="autofillWithResume"]': _locator(),
        '[data-automation-id="SignInWithEmailButton"]': email_signin_locator,
        '[data-automation-id="createAccountLink"]': _locator(),
        '[data-automation-id="createAccountCheckbox"]': _locator(count=checkbox_count),
        '[data-automation-id="createAccountSubmitButton"]': _locator(enabled=submit_enabled),
    }
    page.locator = MagicMock(side_effect=lambda sel: locators[sel])
    return page


async def test_dry_run_apply_fills_account_fields_and_reaches_submit() -> None:
    page = _page()
    plugin = WorkdayPlugin()

    result = await plugin.dry_run_apply(
        page,
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        phone="+1 555 0100",
        cv_path="/tmp/cv.pdf",
    )

    assert result.success is True
    assert result.submit_button_reached is True
    assert result.fields_filled == [
        "email",
        "password",
        "verifyPassword",
        "createAccountCheckbox",
    ]
    page.fill.assert_any_call('[data-automation-id="email"]', "ada@example.com")


async def test_dry_run_apply_never_clicks_create_account_submit() -> None:
    page = _page()
    plugin = WorkdayPlugin()
    submit_locator = page.locator('[data-automation-id="createAccountSubmitButton"]')
    submit_locator.click.reset_mock()

    await plugin.dry_run_apply(
        page,
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        phone="+1 555 0100",
        cv_path="/tmp/cv.pdf",
    )

    submit_locator.click.assert_not_called()


async def test_dry_run_apply_never_fills_the_honeypot_field() -> None:
    page = _page()
    plugin = WorkdayPlugin()

    await plugin.dry_run_apply(
        page,
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        phone="+1 555 0100",
        cv_path="/tmp/cv.pdf",
    )

    for call in page.fill.call_args_list:
        assert "beecatcher" not in call.args[0]


async def test_dry_run_apply_skips_email_signin_button_when_absent() -> None:
    """Some tenants land directly on Create Account without an
    intermediate 'Sign in with email' button."""
    page = _page(email_signin_button_present=False)
    plugin = WorkdayPlugin()

    result = await plugin.dry_run_apply(
        page,
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        phone="+1 555 0100",
        cv_path="/tmp/cv.pdf",
    )

    email_signin = page.locator('[data-automation-id="SignInWithEmailButton"]')
    email_signin.click.assert_not_called()
    assert result.success is True


async def test_dry_run_apply_reports_failure_when_apply_button_never_appears() -> None:
    page = _page()
    apply_locator = page.locator('[data-automation-id="adventureButton"]')
    apply_locator.first.wait_for = AsyncMock(side_effect=TimeoutError("no adventureButton"))
    plugin = WorkdayPlugin()

    result = await plugin.dry_run_apply(
        page,
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        phone="+1 555 0100",
        cv_path="/tmp/cv.pdf",
    )

    assert result.success is False
    assert result.submit_button_reached is False
    assert result.fields_filled == []
    assert result.error is not None
