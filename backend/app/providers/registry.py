"""The list of enabled providers. `job_service.py` iterates this — adding
or removing a source is a one-line change here, nothing else in the
application needs to know.

Indeed and Wellfound were removed rather than left as stubs: neither has
a free public search API anymore, and the only ways to get their listings
are a paid/approved partnership or ToS-violating scraping — not something
to silently retry-and-fail on every search cycle. Revisit if either opens
a real API back up.

`CompanyCareerProvider` takes a URL per instance, so it isn't a singleton
like the others; add one entry per tracked company career page here once
that's configurable (settings/DB), rather than hardcoding company URLs.
"""

from __future__ import annotations

from app.providers.base import Provider
from app.providers.google_jobs import GoogleJobsProvider
from app.providers.greenhouse import GreenhouseProvider
from app.providers.lever import LeverProvider
from app.providers.remoteok import RemoteOKProvider


def get_enabled_providers() -> list[Provider]:
    return [
        RemoteOKProvider(),
        GoogleJobsProvider(),
        GreenhouseProvider(),
        LeverProvider(),
    ]
