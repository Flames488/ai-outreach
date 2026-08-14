"""ATS plugin contract (Phase 3 §ATS plugins).

One plugin per Applicant Tracking System, each knowing that system's own
form structure. `app/playwright/plugins/registry.py` picks a plugin by
URL match; adding a new ATS is a new class here plus one line in the
registry, never a change to `PlaywrightApplicationRunner`.

This phase only implements `dry_run_apply` — fill the form, upload the
CV, locate the submit control, and stop. Never click it. Real submission
is a later phase, gated behind `ENABLE_AUTO_APPLY`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from playwright.async_api import Page


@dataclass
class DryRunResult:
    success: bool
    submit_button_reached: bool
    fields_filled: list[str] = field(default_factory=list)
    error: str | None = None


class ATSPlugin(ABC):
    name: str

    @abstractmethod
    def matches(self, url: str) -> bool:
        """Whether this plugin knows how to handle the given application URL."""

    @abstractmethod
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
        """Fill the application form and locate (never click) the submit
        control."""
