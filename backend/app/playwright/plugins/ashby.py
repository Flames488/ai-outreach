"""Ashby ATS plugin (Phase 3).

Verified against two live `jobs.ashbyhq.com/<company>/<posting-id>`
postings with genuinely different per-tenant UIs for the same platform:
one has a bottom "Apply for this job" button that client-side-routes to
`.../application`; another instead has an "Application" tab
(`role="tab"`) alongside "Overview" at the top of the page. This plugin
tries both entry points — tab first, since it was the more common shape
observed. Either way, no account-creation gate (unlike Workday) — it's a
single-page form like Greenhouse/Lever once reached.

Standard fields are Ashby's own "system fields", stable across postings:
`#_systemfield_name` (a single full-name field, like Lever — not split
first/last), `#_systemfield_email`, and `#_systemfield_resume` (file
upload). Phone is **not** a reliably-named system field — on the tenant
that has it, it renders as a plain `input[type="tel"]` with a UUID name,
not `_systemfield_phone` — so it's matched by input type, not name, and
treated as optional either way (Ashby lets each company toggle which
fields appear per posting, same as Greenhouse's country or Lever's
location being best-effort). The submit control has an explicit, stable
class (`ashby-application-form-submit-button`) reading "Submit
Application" — clearly Ashby's own platform chrome, not per-company
customized.

Two things specific to Ashby, both load-bearing for how this plugin is
written:

1. **CSP blocks `unsafe-eval`.** Ashby's pages set a strict
   Content-Security-Policy that rejects `eval()`-based script injection —
   `Page.wait_for_function()` (which evaluates a JS string) throws under
   it. This plugin only uses selector-based waits (`wait_for_selector`,
   `locator.wait_for()`), which use Playwright's own internal protocol,
   not in-page `eval`, so they're unaffected.
2. **reCAPTCHA scripts load on this domain** (`recaptcha.net`,
   `google.com/recaptcha`) — Ashby forms can be reCAPTCHA-protected. This
   plugin never interacts with a captcha widget in any way; it only fills
   named fields and stops at the submit button, same "never bypass
   anti-bot measures" rule as every other plugin here.

The custom, per-posting application questions (UUID-named text/textarea/
radio/checkbox fields, including EEOC-style demographic questions) are
left untouched — same policy as Greenhouse's "question_*" fields and
Lever's "cards[...]" fields: they vary per job and aren't required for a
dry run to count as successful.
"""

from __future__ import annotations

import re

from playwright.async_api import Page

from app.playwright.plugins.base import ATSPlugin, DryRunResult

_SUBMIT_TEXT = re.compile(r"submit application", re.IGNORECASE)


class AshbyPlugin(ATSPlugin):
    name = "ashby"

    def matches(self, url: str) -> bool:
        return "ashbyhq.com" in url

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
            await self._open_application_form(page)

            await page.wait_for_selector("#_systemfield_name", state="attached")

            await page.fill("#_systemfield_name", full_name)
            fields_filled.append("name")
            await page.fill("#_systemfield_email", email)
            fields_filled.append("email")

            phone_input = page.locator('input[type="tel"]')
            if await phone_input.count():
                await phone_input.first.fill(phone)
                fields_filled.append("phone")

            resume_input = page.locator("#_systemfield_resume")
            if await resume_input.count():
                await resume_input.set_input_files(cv_path)
                fields_filled.append("resume")

            submit = page.get_by_role("button", name=_SUBMIT_TEXT)
            if await submit.count() == 0:
                submit = page.locator(".ashby-application-form-submit-button")
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
        """Two real, different entry points observed across tenants — an
        "Application" tab next to "Overview", or a bottom "Apply for this
        job"/"Apply" button. Tries both; if neither is present *and the
        name field isn't either*, the page may simply still be loading —
        this waits and re-checks rather than concluding "already on the
        form" from what could just be a page that hasn't painted yet
        (`application_runner.py` hands control to the plugin only ~1s
        after navigation, well before Ashby's SPA reliably finishes
        rendering its own entry point).

        Also retries the click itself: on a couple of live tenants the
        tab/button was present and clickable in the DOM sense (Playwright
        clicked it without error) well before the SPA had actually
        attached its real event handler, so the click landed on an inert
        element and nothing happened — a hydration race, not a missing
        element. Re-clicking after a short pause reliably recovers.
        """
        name_field = page.locator("#_systemfield_name")
        # Job descriptions frequently contain the word "apply" in body
        # text and headings (e.g. "Why You Should or Shouldn't Apply") —
        # an unanchored substring match risked clicking a content link
        # instead of the real CTA button. Anchoring at the start avoids
        # that; the plain "^apply" fallback covers postings phrased just
        # "Apply" or "Apply Now" rather than "Apply for this job".
        tab = page.get_by_role("tab", name=re.compile(r"application", re.IGNORECASE))
        apply_primary = page.get_by_role(
            "button", name=re.compile(r"apply for this job", re.IGNORECASE)
        )
        apply_fallback = page.get_by_role("button", name=re.compile(r"^apply", re.IGNORECASE))

        for _attempt in range(8):
            if await name_field.count():
                return

            clicked = False
            for candidate in (tab, apply_primary, apply_fallback):
                if await candidate.count():
                    await candidate.first.click()
                    clicked = True
                    break

            if not clicked:
                # Page likely still loading its own entry point — wait
                # and re-check everything on the next iteration, rather
                # than assuming there's nothing to click.
                await page.wait_for_timeout(2000)
                continue

            try:
                await name_field.wait_for(state="attached", timeout=3000)
                return
            except Exception:  # noqa: BLE001
                continue
