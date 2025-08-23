#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common.sh"

FRONTEND_PORT="${FRONTEND_PORT:-5173}"

usage() {
  cat <<'USAGE'
Usage: FRONTEND_PORT=5173 bash scripts/view.sh [--no-install]
Starts ESBuild dev server (view layer) in app/.
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

log "Starting ESBuild on :${FRONTEND_PORT}"
(
  cd "${ROOT_DIR}/app"
  PORT="${FRONTEND_PORT}" node esbuild.config.js --serve \
    >"${LOG_DIR}/frontend.out.log" 2>"${LOG_DIR}/frontend.err.log" &
  echo $! > "${LOG_DIR}/frontend.pid"
)

wait_for_http "http://localhost:${FRONTEND_PORT}" 60
log "Frontend ready at http://localhost:${FRONTEND_PORT}"
