#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common.sh"

BACKEND_FIRST="${BACKEND_FIRST:-true}"
BACKEND_PORT="${BACKEND_PORT:-8001}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
OPEN="${OPEN:-true}"

usage() {
  cat <<'USAGE'
Master orchestrator for FrankTheLocalLLM (Git Bash).
Env vars:
  BACKEND_FIRST=true|false   # start order
  BACKEND_PORT=8001
  FRONTEND_PORT=5173
  OPEN=true|false            # open browser when ready

Examples:
  BACKEND_FIRST=true bash scripts/master.sh
  BACKEND_FIRST=false BACKEND_PORT=8002 FRONTEND_PORT=5174 bash scripts/master.sh
USAGE
}

bash "${SCRIPT_DIR}/logs.sh" init

log "Configuration: BACKEND_FIRST=${BACKEND_FIRST} BACKEND_PORT=${BACKEND_PORT} FRONTEND_PORT=${FRONTEND_PORT}"

if [[ "${BACKEND_FIRST}" == "true" ]]; then
  bash "${SCRIPT_DIR}/backend.sh"
  BACK_URL="http://localhost:${BACKEND_PORT}/api/hello"
  log "Backend healthy at ${BACK_URL}"
  bash "${SCRIPT_DIR}/frontend.sh"
else
  bash "${SCRIPT_DIR}/frontend.sh"
  bash "${SCRIPT_DIR}/backend.sh"
fi

APP_URL="http://localhost:${FRONTEND_PORT}"
log "Services are up. Frontend: ${APP_URL}"
[[ "${OPEN}" == "true" ]] && open_browser "${APP_URL}"

log "PIDs: backend=$(cat "${LOG_DIR}/backend.pid" 2>/dev/null || echo '?') frontend=$(cat "${LOG_DIR}/frontend.pid" 2>/dev/null || echo '?')"
log "Press Ctrl+C to stop (you may need to kill PIDs manually if shell doesn’t forward signals on Windows)."
wait
