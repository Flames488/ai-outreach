"""Playwright browser lifecycle (Phase 3 §Playwright — the browser engine
the ATS plugins run against).

One Chromium instance per `BrowserEngine`, a fresh, isolated context per
`session()` call — attempts never leak cookies/storage state into each
other. This phase only ever drives dry runs (see `application_runner.py`);
real submission is gated behind `ENABLE_AUTO_APPLY`, which stays false.

`PLAYWRIGHT_HEADLESS` defaults to true, but some ATS platforms fingerprint
and block headless Chromium at the network layer (observed on
job-boards.greenhouse.io — see `README.md`'s "Known limitation" section).
`headless=false` is the documented workaround, not a fingerprint bypass.
"""

from __future__ import annotations

import re
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from playwright.async_api import Browser, Page, Playwright, async_playwright

from app.config.settings import get_settings
from app.utils.retry import async_retry_with_backoff

# Screenshot names are derived from job fingerprints, which embed a raw
# URL (colons, slashes) — invalid in a Windows path. Anything that isn't
# filename-safe becomes an underscore.
_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]")


class PlaywrightTransientError(Exception):
    """The browser couldn't be launched, or a page couldn't be reached,
    after retries — an infra hiccup, not a form/selector failure (those
    stay inside `DryRunResult.error`, never raised). Worth a Celery-level
    retry of the whole attempt."""


class BrowserEngine:
    def __init__(self) -> None:
        settings = get_settings()
        self._headless = settings.playwright_headless
        self._timeout_ms = settings.playwright_timeout
        self._slowmo_ms = settings.playwright_slowmo
        self._screenshot_dir = Path(settings.playwright_screenshot_dir)
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None

    async def start(self) -> None:
        playwright = await async_playwright().start()
        self._playwright = playwright
        try:
            self._browser = await self._launch()
        except Exception as exc:
            # Nothing to stop() — the browser never came up — but the
            # Playwright driver process did start; shut it down cleanly
            # rather than leaking it.
            await playwright.stop()
            self._playwright = None
            raise PlaywrightTransientError(f"Could not launch Chromium: {exc}") from exc

    @async_retry_with_backoff(max_attempts=2, base_delay_seconds=2.0)
    async def _launch(self) -> Browser:
        assert self._playwright is not None
        # channel="chromium" pins the full Chromium build rather than the
        # separate "headless shell" binary Playwright defaults headless
        # mode to since ~1.5x — that's a second download
        # (`playwright install chromium-headless-shell`) this doesn't
        # need when full Chromium is already present.
        return await self._playwright.chromium.launch(
            headless=self._headless, slow_mo=self._slowmo_ms or None, channel="chromium"
        )

    async def stop(self) -> None:
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None

    async def __aenter__(self) -> BrowserEngine:
        await self.start()
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        await self.stop()

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[Page, None]:
        if self._browser is None:
            raise RuntimeError("BrowserEngine.start() must be called before session()")
        # No explicit user_agent override — Playwright's default UA
        # accurately reflects the actual bundled Chromium build.
        # A previous hardcoded string (a stale "Chrome/130.0" against an
        # actual Chrome 151 engine) risked exactly the kind of
        # fingerprint mismatch that anti-bot/feature-detection logic on
        # some ATS platforms (observed intermittently on Ashby) can
        # react to unpredictably.
        context = await self._browser.new_context(viewport={"width": 1366, "height": 900})
        context.set_default_timeout(self._timeout_ms)
        page = await context.new_page()
        try:
            yield page
        finally:
            await context.close()

    async def screenshot(self, page: Page, name: str) -> str:
        self._screenshot_dir.mkdir(parents=True, exist_ok=True)
        safe_name = _UNSAFE_FILENAME_CHARS.sub("_", name)
        # Truncate from the front, not the back — callers put the
        # differentiating "-before"/"-after" suffix at the end, and a
        # long URL-derived prefix (Workday's job URLs especially) must
        # not be allowed to eat it. Kept short (not just under Windows'
        # 260-char MAX_PATH) since the *directory* prefix length is out
        # of this method's control and can itself already be long.
        safe_name = safe_name[-80:]
        path = self._screenshot_dir / f"{safe_name}.png"
        await page.screenshot(path=str(path), full_page=True)
        return str(path)
