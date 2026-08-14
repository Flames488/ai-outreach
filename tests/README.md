# tests/ (integration)

Cross-service integration/e2e tests — full Docker Compose stack, real
Postgres/Redis, HTTP calls against the running API. Unit tests for
individual services live under `backend/tests/` instead, next to the code
they cover.

Empty in Phase 1; populated as later phases add real end-to-end flows
(search -> score -> apply -> notify).
