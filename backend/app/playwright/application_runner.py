"""Playwright-driven form filling and (eventually) submission.

This phase: dry runs only. `dry_run()` drives a real ATS plugin through
navigate -> fill -> upload CV -> locate the submit control, captures
before/after screenshots, and stops — it never clicks submit. `apply()`
(real submission) stays `NotImplementedError`; that's a later phase,
gated behind `ENABLE_AUTO_APPLY`, which stays false.
"""

from __future__ import annotations

from flames_shared.dto import ApplicationRecord, CoverLetterDraft, JobPosting
from flames_shared.enums import ApplicationStatus
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from app.playwright.browser_engine import BrowserEngine, PlaywrightTransientError
from app.playwright.interface import ApplicationRunnerInterface
from app.playwright.plugins.registry import get_plugin_for_url
from app.utils.retry import async_retry_with_backoff

_NAVIGATION_EXCEPTIONS = (PlaywrightError, PlaywrightTimeoutError)


@async_retry_with_backoff(max_attempts=2, base_delay_seconds=2.0, exceptions=_NAVIGATION_EXCEPTIONS)
async def _goto(page: Page, url: str) -> None:
    await page.goto(url, wait_until="domcontentloaded")


class PlaywrightApplicationRunner(ApplicationRunnerInterface):
    async def apply(self, job: JobPosting, cover_letter: CoverLetterDraft) -> ApplicationRecord:
        raise NotImplementedError("Real application submission is implemented in a later phase")

    async def dry_run(
        self,
        *,
        url: str,
        job_fingerprint: str,
        first_name: str,
        last_name: str,
        email: str,
        phone: str,
        cv_path: str,
    ) -> ApplicationRecord:
        plugin = get_plugin_for_url(url)
        if plugin is None:
            return ApplicationRecord(
                job_fingerprint=job_fingerprint,
                status=ApplicationStatus.FAILED,
                method="playwright_dry_run",
                reason=f"No ATS plugin recognizes this URL: {url}",
            )

        engine = BrowserEngine()
        await engine.start()
        try:
            async with engine.session() as page:
                try:
                    await _goto(page, url)
                except _NAVIGATION_EXCEPTIONS as exc:
                    raise PlaywrightTransientError(
                        f"Could not reach {url} after retries: {exc}"
                    ) from exc
                # `domcontentloaded` fires before a heavy client-rendered
                # SPA (Workday especially) has painted anything — a
                # "before" screenshot taken immediately can be blank. A
                # fixed delay isn't reliable (Workday's own job detail
                # page can take well over a second to paint), so this
                # waits for the page to actually have rendered *some*
                # visible text — a generic, plugin-agnostic readiness
                # signal, not an ATS-specific selector.
                try:
                    await page.wait_for_function(
                        "document.body && document.body.innerText.trim().length > 50",
                        timeout=20000,
                    )
                except Exception:  # noqa: BLE001
                    pass
                # The content-readiness condition above can resolve from
                # DOM text that exists before the browser has painted a
                # frame (e.g. a cookie-consent banner's own text) — this
                # settle window is for the paint, not for more content.
                await page.wait_for_timeout(800)
                before_screenshot = await engine.screenshot(page, f"{job_fingerprint}-before")
                result = await plugin.dry_run_apply(
                    page,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    phone=phone,
                    cv_path=cv_path,
                )
                after_screenshot = await engine.screenshot(page, f"{job_fingerprint}-after")
        finally:
            await engine.stop()

        success = result.success and result.submit_button_reached
        return ApplicationRecord(
            job_fingerprint=job_fingerprint,
            status=ApplicationStatus.PENDING_VERIFICATION if success else ApplicationStatus.FAILED,
            method=f"playwright_dry_run:{plugin.name}",
            reason=result.error,
            artifacts={
                "dry_run": True,
                "submit_button_reached": result.submit_button_reached,
                "fields_filled": result.fields_filled,
                "before_screenshot": before_screenshot,
                "after_screenshot": after_screenshot,
            },
        )
