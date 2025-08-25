#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common.sh"

WORKER_OUT="${LOG_DIR}/celery_worker.out.log"
WORKER_ERR="${LOG_DIR}/celery_worker.err.log"

ensure_venv
set -a
source "${ROOT_DIR}/.env" 2>/dev/null || true
set +a

log "Starting Celery worker"
(
  cd "${ROOT_DIR}" && \
  celery -A backend.app.tasks worker --pool=solo >>"${WORKER_OUT}" 2>>"${WORKER_ERR}" &
  echo $! > "${LOG_DIR}/celery_worker.pid"
)

for i in {1..30}; do
  if celery -A backend.app.tasks inspect ping >/dev/null 2>&1; then
    log "Celery worker is running"
    exit 0
  fi
  sleep 1
done

die "Celery worker failed to start or cannot reach Redis"
