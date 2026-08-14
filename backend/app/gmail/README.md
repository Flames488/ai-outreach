# Gmail

OAuth 2.0 + raw message fetching. `app/services/email_service.py` is what
the rest of the app actually calls — it also owns classification (via
`AIService`) and dedup, neither of which lives here.

- `oauth.py` — `build_consent_url()`, `exchange_code_for_credentials()`
- `interface.py` — `GmailClientInterface`: `fetch_messages_since()`
- `client.py` — `GmailClient`, the concrete implementation (`googleapiclient`)

## Status

Fully implemented. Scopes are read-only (`gmail.readonly`, `gmail.labels`)
— Flames never sends or modifies mail. The refresh token is stored
Fernet-encrypted on `users.google_refresh_token_encrypted`
(`app/utils/encryption.py`, keyed by `MASTER_ENCRYPTION_KEY`), never in
plaintext. An `invalid_grant` (or similar) failure during sync marks
`users.gmail_connected = False` and fires a `SYSTEM`-priority
notification rather than failing the sync task silently.

The monitored inbox is `emmanuelnwobodo38@gmail.com` (see `.env.example`).
