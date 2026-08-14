#!/usr/bin/env bash
# One-time local setup: create .env from the template if it doesn't exist yet.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from .env.example — fill in real credentials before starting the stack."
else
    echo ".env already exists, leaving it untouched."
fi

echo ""
echo "Next steps:"
echo "  1. Edit .env: at minimum set SECRET_KEY, JWT_SECRET, POSTGRES_PASSWORD, MASTER_ENCRYPTION_KEY, SEED_ADMIN_PASSWORD."
echo "     (Groq/DeepSeek/Telegram/Google credentials can stay blank until you reach the features that use them.)"
echo "  2. docker compose build"
echo "  3. docker compose up -d"
echo "     (the 'migrate' service runs Alembic to head automatically before api/celery_worker/celery_beat start)"
echo "  4. docker compose run --rm api uv run python scripts/seed.py"
echo "     (creates the initial admin user, default feature flags, and starter application_rules)"
