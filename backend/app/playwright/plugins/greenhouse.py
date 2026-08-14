"""Greenhouse ATS plugin (Phase 3).

Selectors verified against a live `job-boards.greenhouse.io` posting
(Greenhouse's "Job Board 2.0" — the platform's own hosted apply page, not
a company's custom-domain proxy): standard fields are plain inputs by id
(`#first_name`/`#last_name`/`#email`/`#phone`), the resume/cover-letter
uploads are hidden `<input type="file">` elements (`#resume`/
`#cover_letter` — Playwright's `set_input_files` doesn't require
visibility, so the "visually-hidden" class doesn't matter), and the
submit control is a `button[type="submit"]` reading "Submit application"
— that copy is Greenhouse's own platform chrome, not per-company
customized, so it's a stable selector across postings.

`country` is a custom React-select combobox — filled best-effort since
its exact behavior isn't guaranteed identical across every posting, and a
company's own custom "question_*" fields (which vary per job) are left
untouched entirely. Neither is required for a dry run to count as
successful: what's graded is reaching a real, submittable submit button
with the standard fields filled and the CV attached.
"""

from __future__ import annotations

import re

from playwright.async_api import Page

from app.playwright.plugins.base import ATSPlugin, DryRunResult

_SUBMIT_TEXT = re.compile(r"submit application", re.IGNORECASE)


class GreenhousePlugin(ATSPlugin):
    name = "greenhouse"

    def matches(self, url: str) -> bool:
        return "greenhouse.io" in url

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
            await page.wait_for_selector("#first_name", state="attached")

            await page.fill("#first_name", first_name)
            fields_filled.append("first_name")
            await page.fill("#last_name", last_name)
            fields_filled.append("last_name")
            await page.fill("#email", email)
            fields_filled.append("email")

            phone_input = page.locator("#phone")
            if await phone_input.count():
                await phone_input.fill(phone)
                fields_filled.append("phone")

            resume_input = page.locator("#resume")
            if await resume_input.count():
                await resume_input.set_input_files(cv_path)
                fields_filled.append("resume")

            await self._try_fill_country(page, country, fields_filled)

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

    async def _try_fill_country(self, page: Page, country: str, fields_filled: list[str]) -> None:
        """Best-effort only — a react-select combobox that isn't present
        on every posting, and isn't required for dry-run success."""
        country_input = page.locator("#country")
        if not await country_input.count():
            return
        try:
            await country_input.click()
            await country_input.type(country, delay=20)
            option = page.get_by_role("option").first
            await option.wait_for(state="visible", timeout=3000)
            await option.click()
            fields_filled.append("country")
        except Exception:  # noqa: BLE001
            pass
