# shared (`flames_shared`)

Cross-module contracts: enums, Pydantic DTOs, and constants. This is the
**only** thing services are allowed to depend on when talking to each other.

- `enums.py` — `JobStatus`, `ApplicationStatus`, `JobSourceType`, `EmailCategory`,
  `NotificationLevel`, `NotificationChannel`, `UserRole`, `AITaskType`, `JobRuleType`, `ErrorCode`
- `dto.py` — `JobPosting`, `MatchResult`, `EmailClassificationResult`,
  `CoverLetterDraft`, `ApplicationRecord`, `EmailEvent`, `NotificationPayload`
- `constants.py` — thresholds and limits referenced by name, never inlined

## Rule

No business logic lives here. If a function does something beyond
constructing/validating data, it belongs in a service, not in `shared`.

Backend services depend on this package via the uv workspace
(`flames-shared`, declared as a workspace source in `backend/pyproject.toml`).
