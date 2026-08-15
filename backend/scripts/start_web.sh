#!/bin/sh
# Render "Docker Command" override, used in place of chaining commands
# with `&&`/quotes directly in Render's UI field — that field doesn't
# reliably shell-parse what's typed into it (observed: it tried to exec
# the whole typed string as one literal command name). A script file
# sidesteps that entirely.
#
# scripts/seed.py is idempotent — safe to run on every boot, not just
# once — so this doubles as how the initial admin user gets created on
# a host (like Render's free tier) with no Shell/Pre-Deploy Command
# access to run it by hand.
set -e
uv run python scripts/seed.py
exec uv run uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
