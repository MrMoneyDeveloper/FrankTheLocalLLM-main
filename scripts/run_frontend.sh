#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common.sh"

OUT_LOG="${LOG_DIR}/frontend.out.log"
ERR_LOG="${LOG_DIR}/frontend.err.log"

( cd "${ROOT_DIR}" && npm install >>"${OUT_LOG}" 2>>"${ERR_LOG}" )
( cd "${ROOT_DIR}/app" && npm install >>"${OUT_LOG}" 2>>"${ERR_LOG}" )

log "Starting frontend"
(
  cd "${ROOT_DIR}/app" && \
  node esbuild.config.js --serve >>"${OUT_LOG}" 2>>"${ERR_LOG}" &
  echo $! > "${LOG_DIR}/frontend.pid"
)

wait_for_http "http://localhost:5173" 60
log "Frontend running on http://localhost:5173"
