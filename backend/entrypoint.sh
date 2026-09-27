#!/bin/sh
# Release Doctor backend container entrypoint.
#
# When the DB_* environment variables are present (injected from AWS Secrets
# Manager by the ECS task definition), compose the async DATABASE_URL from
# them. Otherwise leave DATABASE_URL as-is (local dev / Railway set it
# directly). Then run migrations and start the API.
set -e

if [ -n "$DB_HOST" ] && [ -z "$DATABASE_URL" ]; then
  export DATABASE_URL="postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
fi

# Initialize the bundled demo repository as a two-commit git repo (clean ->
# risky) so the flagship end-to-end demo works out of the box. Idempotent.
DEMO_REPO="${DEMO_REPO_PATH:-/demo-repository}"
if [ -f "$DEMO_REPO/init-git.sh" ]; then
  # Containers may run as a non-owner of the mounted/copied files; allow git.
  git config --global --add safe.directory "$DEMO_REPO" 2>/dev/null || true
  sh "$DEMO_REPO/init-git.sh" "$DEMO_REPO" || echo "demo repo init skipped/failed (non-fatal)"
fi

# Apply migrations. Tables also auto-create on startup, so a failure here
# (e.g. no migrations yet) is non-fatal.
alembic upgrade head || echo "alembic step skipped/failed - tables auto-create on startup"

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
