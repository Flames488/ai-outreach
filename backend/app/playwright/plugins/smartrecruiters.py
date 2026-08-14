"""SmartRecruiters ATS plugin (Phase 3).

**This plugin is different from every other one in this package: its
selectors are not DOM-verified.** SmartRecruiters' apply flow
(`jobs.smartrecruiters.com/oneclick-ui/...`) is protected platform-wide
by DataDome — confirmed via a plain `curl` (no browser, no Playwright,
no fingerprint involved) returning `403 Forbidden` with a CAPTCHA
challenge on the apply endpoint itself, across multiple unrelated
companies using SmartRecruiters. That's a categorically different, and
stronger, obstacle than Greenhouse's headless-fingerprint block (fixed by
going headed) or Lever's CAPTCHA-gated *submit button* (the button is
still reachable, just not clickable): here, the wall sits in front of the
page even loading, so there is no live DOM to inspect or verify against.

Consistent with this project's "never bypass CAPTCHAs or anti-bot
measures" rule (already applied to Greenhouse and Lever), no attempt was
made to get past DataDome — no stealth plugins, no fingerprint spoofing,
no CAPTCHA solving. Instead, field selectors here are built from
SmartRecruiters' own public, documented Application API schema
(`https://developers.smartrecruiters.com/docs/post-an-application`):
`firstName`, `lastName`, `email`, `phoneNumber`, `resume`. Real ATS web
forms commonly reuse their backend API's field names as HTML `name`
attributes, but that's an informed assumption, not a confirmed fact for
this platform — each field lookup below tries the documented name first,
then a couple of generic fallbacks (by `type` attribute, matching the
pattern that proved necessary for Ashby's undocumented phone field), so
a name mismatch degrades gracefully rather than failing outright.

Operationally: if DataDome relaxes or a legitimate path around it exists
(e.g. running from a trusted network, or SmartRecruiters granting a
partner exemption), this plugin should be re-verified against a real
apply form and this docstring updated — the fallback-heavy selectors
here are a deliberate, honest stand-in until that's possible, not a
final answer.
"""

from __future__ import annotations

import re

from playwright.async_api import Page

from app.playwright.plugins.base import ATSPlugin, DryRunResult

_SUBMIT_TEXT = re.compile(r"submit application|submit", re.IGNORECASE)
_APPLY_TEXT = re.compile(r"^apply", re.IGNORECASE)


class SmartRecruitersPlugin(ATSPlugin):
    name = "smartrecruiters"

    def matches(self, url: str) -> bool:
        return "smartrecruiters.com" in url

    async def dry_run_apply(
        self,
        page: Page,
        *,
        first_name: str,
        last_name: str,
        email: str,
        phone: str,
        cv_path: str,
        country: str = "United States",
    ) -> DryRunResult:
        fields_filled: list[str] = []
        try:
            await self._open_application_form(page)

            first_name_input = await self._first_present(
                page, ['input[name="firstName"]', "#firstName"]
            )
            await first_name_input.fill(first_name)
            fields_filled.append("first_name")

            last_name_input = await self._first_present(
                page, ['input[name="lastName"]', "#lastName"]
            )
            await last_name_input.fill(last_name)
            fields_filled.append("last_name")

            email_input = await self._first_present(
                page, ['input[name="email"]', "#email", 'input[type="email"]']
            )
            await email_input.fill(email)
            fields_filled.append("email")

            phone_input = await self._first_present_optional(
                page, ['input[name="phoneNumber"]', "#phoneNumber", 'input[type="tel"]']
            )
            if phone_input is not None:
                await phone_input.fill(phone)
                fields_filled.append("phone")

            resume_input = page.locator('input[type="file"]')
            if await resume_input.count():
                await resume_input.first.set_input_files(cv_path)
                fields_filled.append("resume")

            submit = page.get_by_role("button", name=_SUBMIT_TEXT)
            if await submit.count() == 0:
                submit = page.locator('button[type="submit"]')
            await submit.first.wait_for(state="visible")
            submit_reached = await submit.first.is_enabled()

            return DryRunResult(
                success=True,
                submit_button_reached=submit_reached,
                fields_filled=fields_filled,
            )
        except Exception as exc:  # noqa: BLE001
            return DryRunResult(
                success=False,
                submit_button_reached=False,
                fields_filled=fields_filled,
                error=str(exc),
            )

    async def _open_application_form(self, page: Page) -> None:
        apply_btn = page.get_by_role("link", name=_APPLY_TEXT)
        if await apply_btn.count() == 0:
            apply_btn = page.get_by_role("button", name=_APPLY_TEXT)
        if await apply_btn.count():
            await apply_btn.first.click()

    async def _first_present(self, page: Page, selectors: list[str]):
        """Try each selector in order, returning the first one actually
        present in the DOM — a documented field name first, then
        progressively more generic fallbacks. Raises if none match,
        for required fields."""
        result = await self._first_present_optional(page, selectors)
        if result is None:
            raise LookupError(f"none of {selectors!r} matched any element on the page")
        return result

    async def _first_present_optional(self, page: Page, selectors: list[str]):
        """Same as `_first_present`, but returns `None` instead of
        raising — for fields SmartRecruiters lets a company disable
        (mirrors Ashby's optional-phone handling)."""
        for selector in selectors:
            locator = page.locator(selector)
            if await locator.count():
                return locator.first
        return None
