#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${ROOT}/logs"
mkdir -p "${LOG_DIR}"
exec > >(tee -a "${LOG_DIR}/run_all.log") 2>&1

run_step() {
  local name="$1"; shift
  echo "--- ${name} ---"
  if ! "$@"; then
    local rc=$?
    echo "Step '${name}' failed with exit code ${rc}" >&2
    tail -n 200 "${LOG_DIR}"/*.err.log 2>/dev/null || true
    exit $rc
  fi
}

run_step "Install dependencies" bash "${ROOT}/scripts/install_deps.sh"
run_step "Write .env" bash "${ROOT}/scripts/ensure_env.sh"
run_step "Start Redis" bash "${ROOT}/scripts/run_redis.sh"
run_step "Start backend" bash "${ROOT}/scripts/run_backend.sh"
run_step "Start Celery worker" bash "${ROOT}/scripts/run_celery_worker.sh"
run_step "Start Celery beat" bash "${ROOT}/scripts/run_celery_beat.sh"
run_step ".NET build and app" bash "${ROOT}/scripts/run_net.sh"
run_step "Start frontend" bash "${ROOT}/scripts/run_frontend.sh"

echo "All components started successfully."
