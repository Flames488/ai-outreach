# Providers

Job-source integrations. Every provider follows the same pipeline:
`search(params)` (query the source, return raw results) → `normalize()`
(convert one raw result to a `StandardJob`, Phase 2's `NormalizedJob`
alias) → `fetch_jobs()` (runs both, defined once in `base.Provider`, never
duplicated per source).

- `base.py` — `Provider` ABC
- `models.py` — `SearchParams`, `StandardJob` (= `NormalizedJob`), the
  provider-agnostic contract (Part 3 §25 / Phase 2 §13)
- `mapping.py` — `standard_job_to_job_posting()`: StandardJob -> the
  cross-service `JobPosting` DTO (used by AI scoring)
- `registry.py` — `get_enabled_providers()`, the single place providers are listed
- `remoteok.py` — real `GET https://remoteok.com/api` call, no auth, no config
- `greenhouse.py`, `lever.py` — real public per-company board APIs, no
  auth; poll `settings.greenhouse_companies_list` /
  `settings.lever_companies_list` (comma-separated board tokens) since
  neither has a generic "search everything" endpoint
- `google_jobs.py` — real, via SerpApi (paid scraper-as-a-service —
  Google itself has no free jobs-search API); raises if `SERPAPI_KEY`
  is unset rather than silently returning nothing
- `company_career.py` — stub, `NotImplementedError`, and not in
  `get_enabled_providers()`

## Status

Indeed and Wellfound were removed entirely (not just left unimplemented):
neither has a free public API anymore, and the only ways to get their
listings are a paid/approved partnership or ToS-violating scraping — not
worth retrying-and-failing on every search cycle. All four registered
providers above are real integrations, not stubs. One provider failing
(bad company token, network error, missing SerpApi key) never aborts the
others — `JobService.search_all()` catches per-provider and continues,
logging the failure to `provider_logs`.

Providers never touch the database — `app/services/job_ingestion_service.py`
is the only thing that maps a `StandardJob` onto a stored `jobs` row
(company lookup/create, salary field-count mapping).

## Adding a source later

`MonsterProvider`, `GlassdoorProvider`, `JobbermanProvider`, and a
ToS-permitting `LinkedInProvider` are the known next candidates — each is a
new file here plus one line in `registry.py`.

## Standard Job Model

`StandardJob`'s field names (`job_title`, `company`, ...) are the
provider-facing contract, not the DB schema. The `jobs` table uses
different names in places (`title`, `company_id`); see
`job_ingestion_service.py` for the explicit mapping.
