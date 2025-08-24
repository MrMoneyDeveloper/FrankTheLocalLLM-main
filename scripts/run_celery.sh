#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common.sh"

WORKER_OUT="${LOG_DIR}/celery_worker.out.log"
WORKER_ERR="${LOG_DIR}/celery_worker.err.log"
BEAT_OUT="${LOG_DIR}/celery_beat.out.log"
BEAT_ERR="${LOG_DIR}/celery_beat.err.log"

ensure_venv

log "Starting Celery worker"
(
  cd "${ROOT_DIR}" && \
  celery -A backend.app.tasks worker --pool=solo >>"${WORKER_OUT}" 2>>"${WORKER_ERR}" &
  echo $! > "${LOG_DIR}/celery_worker.pid"
)

log "Starting Celery beat"
(
  cd "${ROOT_DIR}" && \
  celery -A backend.app.tasks beat >>"${BEAT_OUT}" 2>>"${BEAT_ERR}" &
  echo $! > "${LOG_DIR}/celery_beat.pid"
)

# wait for worker to respond
for i in {1..30}; do
  if celery -A backend.app.tasks inspect ping >/dev/null 2>&1; then
    if kill -0 "$(cat "${LOG_DIR}/celery_beat.pid")" 2>/dev/null; then
      log "Celery worker and beat are running"
      exit 0
    fi
  fi
  sleep 1
done

die "Celery failed to start or cannot reach Redis"
