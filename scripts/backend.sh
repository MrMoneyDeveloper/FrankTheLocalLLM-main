#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common.sh"

BACKEND_PORT="${BACKEND_PORT:-8001}"
API_HEALTH="http://localhost:${BACKEND_PORT}/api/hello"

usage() {
  cat <<'USAGE'
Usage: BACKEND_PORT=8001 bash scripts/backend.sh [--no-install]
Starts FastAPI backend (backend/app/main.py) on BACKEND_PORT.
USAGE
}

NO_INSTALL=false
[[ "${1:-}" == "--no-install" ]] && NO_INSTALL=true

mkdir -p "${LOG_DIR}"

log "Freeing backend port ${BACKEND_PORT}"
free_port "${BACKEND_PORT}"

ensure_venv
if ! $NO_INSTALL; then
  req="${ROOT_DIR}/backend/requirements.txt"
  [[ -f "${req}" ]] && pip install -r "${req}"
fi

log "Starting backend on :${BACKEND_PORT}"
(
  cd "${ROOT_DIR}"
  export PORT="${BACKEND_PORT}"
  python -m backend.app.main \
    >"${LOG_DIR}/backend.out.log" 2>"${LOG_DIR}/backend.err.log" &
  echo $! > "${LOG_DIR}/backend.pid"
)

wait_for_http "${API_HEALTH}" 90
log "Backend ready at ${API_HEALTH}"
