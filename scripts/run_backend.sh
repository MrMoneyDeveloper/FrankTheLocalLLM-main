#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common.sh"

OUT_LOG="${LOG_DIR}/backend.out.log"
ERR_LOG="${LOG_DIR}/backend.err.log"
PING_LOG="${LOG_DIR}/backend_ping.log"

ensure_venv
export REDIS_URL="${REDIS_URL:-redis://127.0.0.1:6379/0}"
export CELERY_BROKER_URL="${REDIS_URL}"
export CELERY_RESULT_BACKEND="${REDIS_URL}"
pip install -r "${ROOT_DIR}/backend/requirements.txt" >>"${OUT_LOG}" 2>>"${ERR_LOG}"
python -m backend.app.manage migrate >>"${OUT_LOG}" 2>>"${ERR_LOG}"

log "Starting FastAPI backend"
(
  cd "${ROOT_DIR}" && \
  python -m backend.app.main >>"${OUT_LOG}" 2>>"${ERR_LOG}" &
  echo $! > "${LOG_DIR}/backend.pid"
)

wait_for_http "http://localhost:8001/api/hello" 30

# Log ping output or error
: >"${PING_LOG}"
{ curl -fsS http://127.0.0.1:8001/api/hello >>"${PING_LOG}" 2>&1; } || true

log "Backend running on http://localhost:8001"
