"""ATS plugin composition root — add a new ATS by adding it to `_PLUGINS`,
never by changing `PlaywrightApplicationRunner`."""

from __future__ import annotations

from app.playwright.plugins.ashby import AshbyPlugin
from app.playwright.plugins.base import ATSPlugin
from app.playwright.plugins.greenhouse import GreenhousePlugin
from app.playwright.plugins.lever import LeverPlugin
from app.playwright.plugins.smartrecruiters import SmartRecruitersPlugin
from app.playwright.plugins.workday import WorkdayPlugin

_PLUGINS: list[ATSPlugin] = [
    GreenhousePlugin(),
    LeverPlugin(),
    WorkdayPlugin(),
    AshbyPlugin(),
    SmartRecruitersPlugin(),
]


def get_plugin_for_url(url: str) -> ATSPlugin | None:
    for plugin in _PLUGINS:
        if plugin.matches(url):
            return plugin
    return None
