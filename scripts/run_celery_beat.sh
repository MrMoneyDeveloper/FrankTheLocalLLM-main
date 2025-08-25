#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common.sh"

BEAT_OUT="${LOG_DIR}/celery_beat.out.log"
BEAT_ERR="${LOG_DIR}/celery_beat.err.log"

ensure_venv
set -a
source "${ROOT_DIR}/.env" 2>/dev/null || true
set +a

log "Starting Celery beat"
(
  cd "${ROOT_DIR}" && \
  celery -A backend.app.tasks beat >>"${BEAT_OUT}" 2>>"${BEAT_ERR}" &
  echo $! > "${LOG_DIR}/celery_beat.pid"
)

for i in {1..30}; do
  if kill -0 "$(cat "${LOG_DIR}/celery_beat.pid")" 2>/dev/null; then
    log "Celery beat is running"
    exit 0
  fi
  sleep 1
done

die "Celery beat failed to start"
