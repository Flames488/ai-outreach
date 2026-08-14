# Playwright (Phase 3 — dry-run application engine)

`app/services/playwright_dry_run_service.py` is what actually gets
called; it wires `PlaywrightApplicationRunner` to the audit trail
(`audit_logs`, action `dry_run_success`/`dry_run_failed`).

- `browser_engine.py` — `BrowserEngine`: Chromium lifecycle, a fresh
  context per attempt, screenshot capture.
- `plugins/base.py` — `ATSPlugin` ABC (`matches(url)`,
  `dry_run_apply(...)`) + `DryRunResult`.
- `plugins/greenhouse.py` — `GreenhousePlugin`, selectors verified
  against a live `job-boards.greenhouse.io` posting.
- `plugins/lever.py` — `LeverPlugin`, selectors verified against a live
  `jobs.lever.co/<company>/<posting-id>/apply` page. Lever has a single
  `name` field (not split first/last), and on some postings the real
  submit is hCaptcha-gated — the dry run stops at the visible submit
  control either way and never attempts the challenge.
- `plugins/workday.py` — `WorkdayPlugin`, verified against a live,
  fully-rendered `<tenant>.wdN.myworkdayjobs.com` posting's real
  click-through flow (Workday is a heavy client-side SPA — nothing here
  came from static HTML). Multi-step and click-driven, unlike
  Greenhouse/Lever's single-page forms: job detail -> `adventureButton`
  ("Apply") -> "Autofill with Resume" -> `createAccountLink` -> the real
  registration form (`email`/`password`/`verifyPassword`/
  `createAccountCheckbox`, submitted via `createAccountSubmitButton`).
  Deliberately stops there — see "Workday stops at account creation"
  below for why.
- `plugins/ashby.py` — `AshbyPlugin`, verified against two live
  `jobs.ashbyhq.com/<company>/<posting-id>` postings with genuinely
  different per-tenant UIs: one has a bottom "Apply for this job" button,
  another an "Application" tab next to "Overview". Tries both. No
  account-creation gate — single-page form like Greenhouse/Lever. Phone
  isn't a reliably-named system field (matched by `input[type="tel"]`,
  not by name). Ashby's CSP blocks `unsafe-eval`, so this plugin only
  uses selector-based waits, never `wait_for_function`.
- `plugins/smartrecruiters.py` — `SmartRecruitersPlugin`. **Not
  DOM-verified**, unlike every other plugin here — SmartRecruiters'
  apply flow is blocked platform-wide by DataDome (a `403` + CAPTCHA
  challenge on the apply endpoint itself, confirmed via plain `curl` with
  no browser involved, across multiple unrelated companies). Selectors
  are built from SmartRecruiters' own public, documented Application API
  schema (`firstName`/`lastName`/`email`/`phoneNumber`/`resume`) with
  generic fallbacks, not a live form. See the module docstring and
  "SmartRecruiters: no live verification" below.
- `plugins/registry.py` — `get_plugin_for_url(url)`, the composition
  root; add a new ATS by adding it here, never by touching
  `application_runner.py`.
- `interface.py` / `application_runner.py` — `ApplicationRunnerInterface`
  and its concrete `PlaywrightApplicationRunner`.

## Status

`dry_run()` is real and working: navigate -> fill the standard fields
(name, email, phone) -> upload the CV -> locate the submit control ->
screenshot before and after -> stop. It never clicks submit.

`apply()` (real submission) still raises `NotImplementedError` — gated
behind `ENABLE_AUTO_APPLY`, which stays `false`. That's a later phase.

`app/tasks/application_tasks.py`'s `apply_to_job` Celery task wires the
dry run into the actual pipeline: `ApplicationService.create_application`
and `.retry_application` enqueue it the moment an application becomes
`QUEUED`. It resolves the default CV and profile, runs the dry run, and
lands the application on `PENDING_VERIFICATION` (ready for a human to
open the filled form and submit it themselves) or `FAILED`/
`REVIEW_REQUIRED` with a reason — gated behind the `enable_playwright`
feature flag and the `/pause` flag, same as search/scoring. Browser
launch and navigation get one retry (`PlaywrightTransientError` in
`browser_engine.py`) before surfacing as a Celery-level retry; a
selector/form failure inside a plugin still only ever produces a
`FAILED` `DryRunResult`, never an exception.

Manual smoke test: `scripts/dry_run_greenhouse.py [job_url]` runs a real
dry run against any live posting whose URL a registered plugin
recognizes (Greenhouse, Lever, Workday, or Ashby — not SmartRecruiters,
see below) and prints a JSON success/failure summary. Despite the
filename (its original scope), it isn't Greenhouse-specific — plugin
selection is by URL via the registry.

## SmartRecruiters: no live verification

Every other plugin in this package was built by actually driving a live
posting and reading its real DOM. SmartRecruiters couldn't be: its apply
infrastructure (`jobs.smartrecruiters.com/oneclick-ui/...`) returns
`403 Forbidden` with a DataDome CAPTCHA challenge — verified with a plain
`curl` request, no browser or automation fingerprint involved, against
multiple unrelated companies' postings. That rules out "it's a
Playwright/headless tell" (Greenhouse's issue) or "the submit button
specifically is gated" (Lever's) — here the wall sits in front of the
page loading at all, so there's no live form to inspect, fill, or
verify against.

Per this project's own "never bypass CAPTCHAs or anti-bot measures"
rule, no attempt was made to get past it — no stealth plugins, no
fingerprint spoofing, no solving the challenge. `plugins/smartrecruiters.py`
is instead built from SmartRecruiters' public, documented Application
API field schema, with generic fallback selectors (by `type` attribute,
same pattern Ashby's undocumented phone field needed) so a documented
name that turns out not to match the real HTML degrades gracefully
rather than failing outright. Its only test coverage is the mocked unit
tests — there is no live dry-run result for this plugin, and the
`fields_filled`/`submit_button_reached` behavior described in its
docstring is an informed best effort, not a confirmed one. Re-verify
against a real form if DataDome access ever becomes possible (a trusted
network, a partner exemption, etc.).

## Workday stops at account creation, by design

Every other plugin here fills fields that stay in the browser's local
DOM until an explicit submit click the dry run never makes — nothing is
sent anywhere until then. Workday's flow is architecturally different:
its own progress bar calls "Create Account" step 1 of 8, and steps 2-8
(Autofill with Resume — where CV upload actually happens — My
Information, My Experience, Application Questions, Voluntary
Disclosures, Review) are only reachable once that account is *real* on
Workday's backend; the wizard's state is genuinely server-persisted per
step, not just held client-side.

This was a real decision point, not an oversight: actually clicking
`createAccountSubmitButton` would create a real, if throwaway, candidate
account on the target company's live recruiting system — a footprint
outside this project's control once made. Asked directly, the operator
chose the conservative option: fill the account-creation fields (email,
password, verify password, the agreement checkbox) with test data, reach
that real submit gate, and stop — the same "never click submit" rule
every other plugin follows, just applied at the point where Workday's
own architecture places the first one. CV upload and the rest of the
wizard are therefore out of scope until either a real user's own account
exists (production, non-dry-run use) or an operator explicitly
authorizes creating a throwaway one against a specific tenant — not
implemented against guessed selectors for screens this plugin has never
actually driven.

The `beecatcher` field on Workday's sign-in/create-account forms is a
honeypot (a classic bot trap) — the plugin only ever touches fields it
explicitly names, so it's never at risk of being filled.

## Known limitation: Workday's initial render time is highly variable

`application_runner.dry_run()` waits for the page to have painted some
real text (not just `domcontentloaded`, which fires before a heavy SPA
renders anything) before taking the "before" screenshot — but on
Workday specifically, that initial paint has been observed anywhere from
~2s to over 10s on the exact same URL, run to run, in this environment.
The bounded wait (~20s) can still lose that race occasionally, producing
a blank "before" screenshot even though the dry run itself (and the
"after" screenshot) succeeds normally — later waits in the click
sequence are per-element and generously bounded, so they tolerate this
fine. Waiting unboundedly for a screenshot would make the tool
unreliable for routine use, so this is accepted as a known, cosmetic
flakiness specific to how slowly Workday's SPA can bootstrap, not a
correctness issue with the dry run itself.

## Lesson: an SPA's own entry point needs to be waited for too, not just its form

`application_runner.dry_run()` hands control to a plugin only shortly
after navigation (a generic content-paint wait, not a full render wait —
see the Workday section above). On Ashby, this meant a plugin's very
first check for its "open the form" trigger (a tab or a button) could
run before that trigger had even rendered — and the original
`_open_application_form` treated "nothing found yet" as "must already be
on the form" and gave up immediately, rather than waiting and checking
again. The result: this passed every mocked unit test (which don't model
render timing) and failed nearly every live run, in a way that looked
like generic ATS-render flakiness but was actually a real, reproducible
logic bug — confirmed by writing a standalone script that *did* wait
before checking, which worked every time.

The fix: `_open_application_form`'s loop now waits and re-checks for its
own entry point (tab/button/already-there) when none of them are found
yet, not just for the resulting form after a click. Any future plugin
whose ATS needs a click to reveal its form should follow the same
pattern — detect-with-retry, not detect-once.

A related, smaller fix in the same investigation: `BrowserEngine` used to
set a hardcoded `user_agent` string (a stale "Chrome/130.0" against an
actually-newer bundled Chromium) on every context, across every plugin.
Removed — Playwright's default UA accurately reflects the real browser
build, and a mismatched one is exactly the kind of fingerprint anomaly
anti-bot logic can react to unpredictably.

## Known limitation: headless mode gets blocked on some ATS platforms

`job-boards.greenhouse.io` returns `net::ERR_TIMED_OUT` for
`headless=True` (Chromium's default) but loads normally with
`headless=False` — verified directly (a plain navigation to
`example.com` succeeds headless; the same navigation to a Greenhouse
posting only succeeds headed). This looks like anti-bot fingerprinting on
Greenhouse's side rejecting a headless browser signature, not a real
network problem.

The fix here is **not** to spoof the headless fingerprint — that would
cross the project's own "never bypass anti-bot measures" rule
([interface.py]/project philosophy below). `PLAYWRIGHT_HEADLESS=false` is
a legitimate accommodation instead: it's still a completely normal,
fully-identified real browser, just with a visible window rather than an
invisible one. In Docker (no display), that requires a virtual display
(e.g. `xvfb-run`) — not yet wired up, since Docker itself is unvalidated
this phase. Until then, `PLAYWRIGHT_HEADLESS` defaults to `true` (correct
for a real headless server), and this is a documented operational
constraint to revisit if it recurs against other ATS platforms.

The Lever dry run was also run headed (`PLAYWRIGHT_HEADLESS=false`,
untested headless) — `jobs.lever.co` is Cloudflare-fronted, a common
source of the same kind of headless fingerprinting, so headed-by-default
is the safer assumption until proven otherwise per ATS.

## Non-negotiable rules (project philosophy)

- Never attempt to bypass CAPTCHAs or other anti-bot/security measures.
- Gracefully skip and log applications that need manual intervention
  (`ApplicationStatus.REVIEW_REQUIRED`), rather than forcing a submission.
- Never submit a duplicate application for the same job fingerprint.
- Dry runs never click submit. Ever.
