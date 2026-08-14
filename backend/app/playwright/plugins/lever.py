"""Lever ATS plugin (Phase 3).

Selectors verified against a live `jobs.lever.co/<company>/<posting-id>/apply`
page: standard fields are plain inputs by `name` attribute
(`name`/`email`/`phone`/`location`), the resume upload is
`input[name="resume"]`, and the user-facing submit control is
`[data-qa="btn-submit"]` (a `type="button"`, not `type="submit"` — Lever
wires it to a JS handler that runs client-side validation, and on some
postings an hCaptcha challenge, before the real hidden
`#hcaptchaSubmitBtn` fires) reading "Submit application" — that copy and
the `data-qa` attribute are Lever's own platform chrome, stable across
postings regardless of whether a given company has hCaptcha enabled.

Unlike Greenhouse, Lever has a single `name` field rather than split
first/last — `full_name` is passed through as-is. Custom per-posting
questions (Lever's "cards[...]" fields) are left untouched, same as
Greenhouse's "question_*" fields: they vary per job and aren't required
for a dry run to count as successful.

This dry run never clicks the submit control — on postings where it's
hCaptcha-gated, clicking would trigger the challenge, and this project
never attempts to bypass CAPTCHAs or other anti-bot measures.
"""

from __future__ import annotations

import re

from playwright.async_api import Page

from app.playwright.plugins.base import ATSPlugin, DryRunResult

_SUBMIT_TEXT = re.compile(r"submit application", re.IGNORECASE)


class LeverPlugin(ATSPlugin):
    name = "lever"

    def matches(self, url: str) -> bool:
        return "lever.co" in url

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
        full_name = f"{first_name} {last_name}".strip()
        try:
            await page.wait_for_selector('input[name="name"]', state="attached")

            await page.fill('input[name="name"]', full_name)
            fields_filled.append("name")
            await page.fill('input[name="email"]', email)
            fields_filled.append("email")

            phone_input = page.locator('input[name="phone"]')
            if await phone_input.count():
                await phone_input.fill(phone)
                fields_filled.append("phone")

            location_input = page.locator('input[name="location"]')
            if await location_input.count():
                await location_input.fill(country)
                fields_filled.append("location")

            resume_input = page.locator('input[name="resume"]')
            if await resume_input.count():
                await resume_input.set_input_files(cv_path)
                fields_filled.append("resume")

            submit = page.get_by_role("button", name=_SUBMIT_TEXT)
            if await submit.count() == 0:
                submit = page.locator('[data-qa="btn-submit"]')
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
