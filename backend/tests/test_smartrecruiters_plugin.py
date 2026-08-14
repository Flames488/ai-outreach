"""Unit tests for the SmartRecruiters ATS plugin's dry-run form-filling
logic (Phase 3) — a fully mocked Page, no real browser needed.

Unlike every other ATS plugin here, this one has **no** live-browser
smoke test: SmartRecruiters' apply flow is blocked platform-wide by
DataDome (see `smartrecruiters.py`'s module docstring), so there is no
live DOM to run against. These mocked tests are this plugin's only
coverage until that changes."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from app.playwright.plugins.smartrecruiters import SmartRecruitersPlugin


def _locator(*, count: int = 1, enabled: bool = True) -> MagicMock:
    locator = MagicMock()
    locator.count = AsyncMock(return_value=count)
    locator.fill = AsyncMock()
    locator.set_input_files = AsyncMock()
    locator.click = AsyncMock()
    first = MagicMock()
    first.click = AsyncMock()
    first.fill = AsyncMock()
    first.set_input_files = AsyncMock()
    first.wait_for = AsyncMock()
    first.is_enabled = AsyncMock(return_value=enabled)
    locator.first = first
    return locator


def _page(
    *,
    apply_link_count: int = 0,
    apply_button_count: int = 0,
    first_name_count: int = 1,
    last_name_count: int = 1,
    email_count: int = 1,
    phone_count: int = 0,
    resume_count: int = 1,
    submit_role_count: int = 1,
    submit_enabled: bool = True,
) -> MagicMock:
    page = MagicMock()

    apply_link_locator = _locator(count=apply_link_count)
    apply_button_locator = _locator(count=apply_button_count)
    submit_role_locator = _locator(count=submit_role_count, enabled=submit_enabled)

    def get_by_role_side_effect(role, name=None):
        pattern = getattr(name, "pattern", "") if name else ""
        if role == "link" and "apply" in pattern.lower():
            return apply_link_locator
        if role == "button" and "apply" in pattern.lower():
            return apply_button_locator
        if role == "button" and "submit" in pattern.lower():
            return submit_role_locator
        raise AssertionError(f"unexpected get_by_role call: {role!r}, {pattern!r}")

    page.get_by_role = MagicMock(side_effect=get_by_role_side_effect)

    locators = {
        'input[name="firstName"]': _locator(count=first_name_count),
        "#firstName": _locator(count=0),
        'input[name="lastName"]': _locator(count=last_name_count),
        "#lastName": _locator(count=0),
        'input[name="email"]': _locator(count=email_count),
        "#email": _locator(count=0),
        'input[type="email"]': _locator(count=0),
        'input[name="phoneNumber"]': _locator(count=phone_count),
        "#phoneNumber": _locator(count=0),
        'input[type="tel"]': _locator(count=0),
        'input[type="file"]': _locator(count=resume_count),
        'button[type="submit"]': _locator(enabled=submit_enabled),
    }
    page.locator = MagicMock(side_effect=lambda sel: locators[sel])
    return page


async def test_dry_run_apply_fills_standard_fields_and_reaches_submit() -> None:
    page = _page()
    plugin = SmartRecruitersPlugin()

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
    assert result.fields_filled == ["first_name", "last_name", "email", "resume"]


async def test_dry_run_apply_fills_phone_when_present() -> None:
    page = _page(phone_count=1)
    plugin = SmartRecruitersPlugin()

    result = await plugin.dry_run_apply(
        page,
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        phone="+1 555 0100",
        cv_path="/tmp/cv.pdf",
    )

    assert "phone" in result.fields_filled


async def test_dry_run_apply_clicks_apply_link_when_present() -> None:
    page = _page(apply_link_count=1)
    plugin = SmartRecruitersPlugin()
    apply_locator = page.get_by_role("link", name=__import__("re").compile("^apply", 0))
    apply_locator.first.click.reset_mock()

    result = await plugin.dry_run_apply(
        page,
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        phone="+1 555 0100",
        cv_path="/tmp/cv.pdf",
    )

    apply_locator.first.click.assert_called_once()
    assert result.success is True


async def test_dry_run_apply_never_clicks_the_submit_button() -> None:
    page = _page()
    plugin = SmartRecruitersPlugin()
    submit_locator = page.get_by_role("button", name=__import__("re").compile("submit", 0))

    await plugin.dry_run_apply(
        page,
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        phone="+1 555 0100",
        cv_path="/tmp/cv.pdf",
    )

    submit_locator.first.click.assert_not_called()


async def test_dry_run_apply_reports_failure_when_required_field_missing() -> None:
    page = _page(first_name_count=0)
    plugin = SmartRecruitersPlugin()

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
