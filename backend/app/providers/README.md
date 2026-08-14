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
- `remoteok.py` — **working end-to-end**: real `GET https://remoteok.com/api` call
- `indeed.py`, `google_jobs.py`, `wellfound.py`, `company_career.py`,
  `greenhouse.py`, `lever.py` — stubs, `NotImplementedError`

## Status

RemoteOK is the one provider implemented end-to-end for Phase 2 (§13:
"pick the one with the simplest public API... the point of this phase is
proving the adapter pattern works, not covering every source"). The other
six raise `NotImplementedError` — `JobService.search_all()` catches that
per-provider and continues, logging the failure to `provider_logs`.

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
