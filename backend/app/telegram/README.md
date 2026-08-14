# Telegram

Bot webhook handling — command router, handlers, and the outbound
Telegram Bot API client. `app/services/notification_service.py` is what
the rest of the app calls to send one-way alerts; this package is for the
interactive bot (commands, inline buttons).

- `interface.py` — `NotificationProvider` ABC
- `client.py` — `TelegramProvider`: `send()` (NotificationProvider),
  `send_message()`, `answer_callback_query()`, `set_webhook()`
- `auth.py` — `get_telegram_user(chat_id)`, separate from the JWT
  dependency chain (Telegram auth is by `telegram_chat_id`, not a token)
- `router.py` — `handle_update()`: parses a Telegram Update, rate-limits
  by chat ID, resolves the user, dispatches to a handler
- `handlers.py` — one function per command + the job-review callback handler
- `keyboards.py` — inline keyboard builders (Job Review flow)

## Phase 2 command scope

`/start`, `/help`, `/status`, `/jobs`, `/today`, `/applications`,
`/review`, `/emails`, `/stats`, `/settings`, `/pause`, `/resume`,
`/health` (admin), `/logs` (admin) are implemented. `/search`, `/apply`,
`/retry` are registered (so `/help` stays accurate) but respond "not yet
available" — they need the Playwright Application Engine, which isn't
built this phase.

## Status

Unauthorized chat IDs (no matching `users.telegram_chat_id`) get "Access
denied" and nothing else runs. Admin-only commands check `user.role ==
ADMIN`. Rate limit: 30 commands/minute per chat ID (same Redis-backed
limiter as the REST API, keyed by chat ID instead of IP).

`/pause` and `/resume` toggle a `feature_flags` row
(`operations_paused`) — `app/scheduler/pause.py` is checked by
`search_tasks`/`ai_tasks` before doing work, so this is a real pause, not
cosmetic.
