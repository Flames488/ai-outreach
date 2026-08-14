"""Unit tests for the Greenhouse ATS plugin's dry-run form-filling logic
(Phase 3) — a fully mocked Page, no real browser needed. Real-browser
coverage lives in the manual smoke test (`scripts/dry_run_greenhouse.py`)
run against a live posting."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from app.playwright.plugins.greenhouse import GreenhousePlugin


def _locator(*, count: int = 1, enabled: bool = True) -> MagicMock:
    locator = MagicMock()
    locator.count = AsyncMock(return_value=count)
    locator.fill = AsyncMock()
    locator.set_input_files = AsyncMock()
    locator.click = AsyncMock()
    locator.type = AsyncMock()
    first = MagicMock()
    first.wait_for = AsyncMock()
    first.is_enabled = AsyncMock(return_value=enabled)
    first.click = AsyncMock()
    locator.first = first
    return locator


def _page(
    *,
    phone_count: int = 1,
    resume_count: int = 1,
    country_count: int = 0,
    submit_role_count: int = 1,
    submit_enabled: bool = True,
) -> MagicMock:
    page = MagicMock()
    page.wait_for_selector = AsyncMock()
    page.fill = AsyncMock()

    locators = {
        "#phone": _locator(count=phone_count),
        "#resume": _locator(count=resume_count),
        "#country": _locator(count=country_count),
        'button[type="submit"]': _locator(count=1, enabled=submit_enabled),
    }
    page.locator = MagicMock(side_effect=lambda sel: locators[sel])
    page.get_by_role = MagicMock(
        return_value=_locator(count=submit_role_count, enabled=submit_enabled)
    )
    return page


async def test_dry_run_apply_fills_standard_fields_and_reaches_submit() -> None:
    page = _page()
    plugin = GreenhousePlugin()

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
    assert result.fields_filled == ["first_name", "last_name", "email", "phone", "resume"]
    page.fill.assert_any_call("#first_name", "Ada")
    page.fill.assert_any_call("#last_name", "Lovelace")
    page.fill.assert_any_call("#email", "ada@example.com")


async def test_dry_run_apply_never_clicks_the_submit_button() -> None:
    page = _page()
    plugin = GreenhousePlugin()
    submit_locator = page.get_by_role.return_value

    await plugin.dry_run_apply(
        page,
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        phone="+1 555 0100",
        cv_path="/tmp/cv.pdf",
    )

    submit_locator.first.click.assert_not_called()


async def test_dry_run_apply_reports_failure_when_form_never_loads() -> None:
    page = _page()
    page.wait_for_selector = AsyncMock(side_effect=TimeoutError("no #first_name on page"))
    plugin = GreenhousePlugin()

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


async def test_dry_run_apply_disabled_submit_is_not_reached() -> None:
    page = _page(submit_enabled=False)
    plugin = GreenhousePlugin()

    result = await plugin.dry_run_apply(
        page,
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        phone="+1 555 0100",
        cv_path="/tmp/cv.pdf",
    )

    assert result.success is True
    assert result.submit_button_reached is False
