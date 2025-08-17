#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common.sh"

FRONTEND_PORT="${FRONTEND_PORT:-5173}"
BACKEND_PORT="${BACKEND_PORT:-8001}"
VITE_API_BASE="${VITE_API_BASE:-http://localhost:${BACKEND_PORT}/api}"

usage() {
  cat <<'USAGE'
Usage: FRONTEND_PORT=5173 BACKEND_PORT=8001 bash scripts/frontend.sh [--no-install]
Starts Vite dev server in app/ with VITE_API_BASE.
USAGE
}

NO_INSTALL=false
[[ "${1:-}" == "--no-install" ]] && NO_INSTALL=true

mkdir -p "${LOG_DIR}"
log "Freeing frontend port ${FRONTEND_PORT}"
free_port "${FRONTEND_PORT}"

if ! $NO_INSTALL; then
  ( cd "${ROOT_DIR}" && npm install >"${LOG_DIR}/npm.root.out.log" 2>"${LOG_DIR}/npm.root.err.log" )
  ( cd "${ROOT_DIR}/app" && npm install >"${LOG_DIR}/npm.app.out.log" 2>"${LOG_DIR}/npm.app.err.log" )
fi

log "Starting Vite on :${FRONTEND_PORT} (VITE_API_BASE=${VITE_API_BASE})"
(
  cd "${ROOT_DIR}/app"
  VITE_API_BASE="${VITE_API_BASE}" npm run dev -- --host 0.0.0.0 --port "${FRONTEND_PORT}" \
    >"${LOG_DIR}/frontend.out.log" 2>"${LOG_DIR}/frontend.err.log" &
  echo $! > "${LOG_DIR}/frontend.pid"
)

wait_for_http "http://localhost:${FRONTEND_PORT}" 60
log "Frontend ready at http://localhost:${FRONTEND_PORT}"
