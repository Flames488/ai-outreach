"""Unit tests for the Ashby ATS plugin's dry-run form-filling logic
(Phase 3) — a fully mocked Page, no real browser needed. Real-browser
coverage lives in the manual smoke test (`scripts/dry_run_greenhouse.py`,
which accepts any registered plugin's URL) run against a live posting."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from app.playwright.plugins.ashby import AshbyPlugin


def _locator(*, count: int = 1, enabled: bool = True) -> MagicMock:
    locator = MagicMock()
    locator.count = AsyncMock(return_value=count)
    locator.fill = AsyncMock()
    locator.set_input_files = AsyncMock()
    locator.click = AsyncMock()
    locator.wait_for = AsyncMock()
    first = MagicMock()
    first.click = AsyncMock()
    first.fill = AsyncMock()
    first.wait_for = AsyncMock()
    first.is_enabled = AsyncMock(return_value=enabled)
    locator.first = first
    return locator


def _page(
    *,
    name_field_count: int = 0,
    name_field_appears_after_click: bool = True,
    tab_count: int = 1,
    apply_primary_count: int = 0,
    apply_fallback_count: int = 0,
    phone_count: int = 0,
    resume_count: int = 1,
    submit_role_count: int = 1,
    submit_enabled: bool = True,
) -> MagicMock:
    page = MagicMock()
    page.wait_for_selector = AsyncMock()
    page.fill = AsyncMock()

    name_field_locator = _locator(count=name_field_count)
    if not name_field_appears_after_click:
        name_field_locator.wait_for = AsyncMock(side_effect=TimeoutError("never appeared"))

    tab_locator = _locator(count=tab_count)
    apply_primary_locator = _locator(count=apply_primary_count)
    apply_fallback_locator = _locator(count=apply_fallback_count)
    submit_role_locator = _locator(count=submit_role_count, enabled=submit_enabled)

    def get_by_role_side_effect(role, name=None):
        pattern = getattr(name, "pattern", "") if name else ""
        if role == "tab" and "application" in pattern.lower():
            return tab_locator
        if role == "button" and "apply for this job" in pattern.lower():
            return apply_primary_locator
        if role == "button" and pattern.lower() == "^apply":
            return apply_fallback_locator
        if role == "button" and "submit" in pattern.lower():
            return submit_role_locator
        raise AssertionError(f"unexpected get_by_role call: {role!r}, {pattern!r}")

    page.get_by_role = MagicMock(side_effect=get_by_role_side_effect)

    locators = {
        "#_systemfield_name": name_field_locator,
        'input[type="tel"]': _locator(count=phone_count),
        "#_systemfield_resume": _locator(count=resume_count),
        ".ashby-application-form-submit-button": _locator(enabled=submit_enabled),
    }
    page.locator = MagicMock(side_effect=lambda sel: locators[sel])
    return page


async def test_dry_run_apply_fills_standard_fields_and_reaches_submit() -> None:
    page = _page()
    plugin = AshbyPlugin()

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
    assert result.fields_filled == ["name", "email", "resume"]
    page.fill.assert_any_call("#_systemfield_name", "Ada Lovelace")
    page.fill.assert_any_call("#_systemfield_email", "ada@example.com")


async def test_dry_run_apply_uses_application_tab_when_present() -> None:
    """One real tenant uses a bottom button; another uses an
    "Application" tab next to "Overview" — the tab takes priority when
    both could theoretically match, and the button path is never
    touched."""
    page = _page(tab_count=1)
    plugin = AshbyPlugin()
    tab_locator = page.get_by_role("tab", name=__import__("re").compile("application", 0))
    tab_locator.first.click.reset_mock()

    result = await plugin.dry_run_apply(
        page,
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        phone="+1 555 0100",
        cv_path="/tmp/cv.pdf",
    )

    tab_locator.first.click.assert_called_once()
    assert result.success is True


async def test_dry_run_apply_falls_back_to_apply_button_when_no_tab() -> None:
    page = _page(tab_count=0, apply_primary_count=1)
    plugin = AshbyPlugin()
    button_locator = page.get_by_role(
        "button", name=__import__("re").compile("apply for this job", 0)
    )
    button_locator.first.click.reset_mock()

    result = await plugin.dry_run_apply(
        page,
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        phone="+1 555 0100",
        cv_path="/tmp/cv.pdf",
    )

    button_locator.first.click.assert_called_once()
    assert result.success is True


async def test_dry_run_apply_fills_phone_when_present_as_tel_input() -> None:
    page = _page(phone_count=1)
    plugin = AshbyPlugin()

    result = await plugin.dry_run_apply(
        page,
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        phone="+1 555 0100",
        cv_path="/tmp/cv.pdf",
    )

    assert "phone" in result.fields_filled


async def test_dry_run_apply_never_clicks_the_submit_button() -> None:
    page = _page()
    plugin = AshbyPlugin()
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


async def test_dry_run_apply_reports_failure_when_form_never_loads() -> None:
    page = _page(name_field_appears_after_click=False)
    page.wait_for_selector = AsyncMock(side_effect=TimeoutError("no #_systemfield_name on page"))
    plugin = AshbyPlugin()

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


async def test_dry_run_apply_skips_click_when_already_on_form() -> None:
    """Some URLs may already point at the /application page directly."""
    page = _page(name_field_count=1, tab_count=0, apply_primary_count=0, apply_fallback_count=0)
    plugin = AshbyPlugin()
    tab_locator = page.get_by_role("tab", name=__import__("re").compile("application", 0))

    result = await plugin.dry_run_apply(
        page,
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        phone="+1 555 0100",
        cv_path="/tmp/cv.pdf",
    )

    tab_locator.first.click.assert_not_called()
    assert result.success is True
