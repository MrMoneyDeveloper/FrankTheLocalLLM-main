#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common.sh"

ENV_FILE="${ROOT_DIR}/.env"
cat > "${ENV_FILE}" <<'ENVEOF'
# Backend settings
REDIS_URL=redis://127.0.0.1:6379/0
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0
CELERY_POOL=solo

# Fast/simplified local mode toggles
# Skip Redis and Celery processes; tasks can run eagerly inside the app.
SKIP_REDIS=1
SKIP_CELERY=1
CELERY_TASK_ALWAYS_EAGER=true
SKIP_DOTNET=1
ENVEOF

log "Wrote ${ENV_FILE} (fast local mode enabled: SKIP_REDIS=1, SKIP_CELERY=1)"
