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
Controller orchestrates the model and view layers.

Commands:
  start         start backend and frontend (default)
  rotate-logs   move logs to logs/archive/<timestamp>/

Env vars:
  BACKEND_FIRST=true|false
  BACKEND_PORT=8001
  FRONTEND_PORT=5173
  OPEN=true|false

Examples:
  BACKEND_FIRST=true bash scripts/controller.sh
  bash scripts/controller.sh rotate-logs
USAGE
}

cmd="${1:-start}"
case "${cmd}" in
  start)
    init_logs
    log "Configuration: BACKEND_FIRST=${BACKEND_FIRST} BACKEND_PORT=${BACKEND_PORT} FRONTEND_PORT=${FRONTEND_PORT}"
    if [[ "${BACKEND_FIRST}" == "true" ]]; then
      bash "${SCRIPT_DIR}/model.sh"
      BACK_URL="http://localhost:${BACKEND_PORT}/api/hello"
      log "Backend healthy at ${BACK_URL}"
      bash "${SCRIPT_DIR}/view.sh"
    else
      bash "${SCRIPT_DIR}/view.sh"
      bash "${SCRIPT_DIR}/model.sh"
    fi
    APP_URL="http://localhost:${FRONTEND_PORT}"
    log "Services are up. Frontend: ${APP_URL}"
    [[ "${OPEN}" == "true" ]] && open_browser "${APP_URL}"
    log "PIDs: backend=$(cat "${LOG_DIR}/backend.pid" 2>/dev/null || echo '?') frontend=$(cat "${LOG_DIR}/frontend.pid" 2>/dev/null || echo '?')"
    log "Press Ctrl+C to stop (you may need to kill PIDs manually if signals are not forwarded)."
    wait
    ;;
  rotate-logs)
    rotate_logs
    ;;
  *)
    usage
    exit 2
    ;;
esac
