"""Workday ATS plugin (Phase 3).

Verified against a live `<tenant>.wdN.myworkdayjobs.com` posting's real,
rendered flow (Workday is a heavy client-side SPA — nothing here was
guessed from static HTML): job detail page -> click the `adventureButton`
("Apply") -> a popup offers "Autofill with Resume" / "Apply Manually" /
"Use My Last Application" -> "Autofill with Resume" lands on a Sign In
screen -> `createAccountLink` switches it to the real registration form
(`email`/`password`/`verifyPassword`/`createAccountCheckbox`, submitted
via `createAccountSubmitButton`). Workday calls this "step 1 of 8" on its
own progress bar.

**Why this plugin stops at step 1, unlike Greenhouse/Lever reaching a
job-specific submit control:** every other ATS plugin here fills fields
that stay client-side (in the browser's DOM) until an explicit submit
click that dry runs never make — nothing is sent anywhere. Workday's
first step is different: `createAccountSubmitButton` is a real account
*registration* call to Workday's backend, and steps 2-8 (Autofill with
Resume — where CV upload actually happens — My Information, My
Experience, Application Questions, Voluntary Disclosures, Review) are
only reachable once that account exists server-side; the wizard's state
is genuinely persisted per step, not just held in local browser state.
Actually clicking through would create a real, if throwaway, candidate
account on the target company's live recruiting system — a footprint
this project won't create without the operator explicitly authorizing it
for a specific, real Workday tenant (see `README.md`).

So this dry run's scope is intentionally narrower here: reach and fill
the real first submit gate Workday's flow presents, verify it's
reachable and enabled, and stop — same "never click submit" rule as
every other plugin, just applied at the point where Workday's own
architecture puts the first real one. CV upload and the rest of the
wizard are documented as out of scope until an authorized account exists
(a real user's account in production, or an operator-approved throwaway
one against a specific tenant), not implemented against guessed
selectors for screens this plugin has never actually seen.

Honeypot note: the Sign In/Create Account forms include a `beecatcher`
input — a classic bot trap (a field a human would never see or fill).
This plugin never touches it, by construction: it only interacts with
fields it explicitly names.
"""

from __future__ import annotations

import uuid

from playwright.async_api import Page

from app.playwright.plugins.base import ATSPlugin, DryRunResult

_COOKIE_ACCEPT = '[data-automation-id="legalNoticeAcceptButton"]'


class WorkdayPlugin(ATSPlugin):
    name = "workday"

    def matches(self, url: str) -> bool:
        return "myworkdayjobs.com" in url

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
            await self._accept_cookies(page)

            apply_btn = page.locator('[data-automation-id="adventureButton"]')
            await apply_btn.first.wait_for(state="visible")
            await apply_btn.first.click()

            autofill_btn = page.locator('[data-automation-id="autofillWithResume"]')
            await autofill_btn.wait_for(state="visible")
            await autofill_btn.click()

            # This client-side route transition renders slowly and
            # inconsistently on the live site (observed: sometimes ready
            # in ~2s, sometimes still blank past 10s) — waiting for the
            # apply-flow container itself, before touching anything
            # inside it, avoids racing the SPA rather than guessing a
            # fixed delay.
            await page.wait_for_selector('[data-automation-id="applyFlowPage"]', state="visible")

            await self._accept_cookies(page)

            # `count()` is a point-in-time DOM snapshot — right after the
            # previous click it can read 0 simply because this button
            # hasn't rendered *yet*, not because the tenant lacks it. A
            # bounded `wait_for` (some tenants skip straight to the
            # email sign-in form, so this is allowed to time out) is the
            # correct "is it here" check mid-transition.
            email_signin_btn = page.locator('[data-automation-id="SignInWithEmailButton"]')
            try:
                await email_signin_btn.wait_for(state="visible", timeout=10000)
                await email_signin_btn.click()
            except Exception:  # noqa: BLE001
                pass

            create_account_link = page.locator('[data-automation-id="createAccountLink"]')
            await create_account_link.wait_for(state="visible")
            await create_account_link.click()

            await page.wait_for_selector('[data-automation-id="email"]', state="attached")

            await page.fill('[data-automation-id="email"]', email)
            fields_filled.append("email")

            password = self._dry_run_password()
            await page.fill('[data-automation-id="password"]', password)
            fields_filled.append("password")
            await page.fill('[data-automation-id="verifyPassword"]', password)
            fields_filled.append("verifyPassword")

            checkbox = page.locator('[data-automation-id="createAccountCheckbox"]')
            if await checkbox.count():
                await checkbox.check()
                fields_filled.append("createAccountCheckbox")

            submit = page.locator('[data-automation-id="createAccountSubmitButton"]')
            await submit.wait_for(state="visible")
            submit_reached = await submit.is_enabled()

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

    async def _accept_cookies(self, page: Page) -> None:
        """Best-effort — the cookie banner can reappear across Workday's
        client-side route transitions, or not show at all if already
        accepted this session."""
        try:
            accept = page.locator(_COOKIE_ACCEPT)
            await accept.wait_for(state="visible", timeout=5000)
            await accept.click()
        except Exception:  # noqa: BLE001
            pass

    def _dry_run_password(self) -> str:
        """Meets Workday's default complexity policy (upper/lower/digit,
        minimum length) — never persisted anywhere, generated fresh per
        run since the account creation submit is never actually clicked."""
        return f"FlamesDryRun-{uuid.uuid4().hex[:12]}!1"
