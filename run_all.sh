#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${ROOT}/logs"
mkdir -p "${LOG_DIR}"
exec > >(tee -a "${LOG_DIR}/run_all.log") 2>&1

# Load optional environment toggles
if [[ -f "${ROOT}/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ROOT}/.env"
  set +a
fi

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

run_step "Write .env" bash "${ROOT}/scripts/ensure_env.sh"
run_step "Install dependencies" bash "${ROOT}/scripts/install_deps.sh"
if [[ "${SKIP_REDIS:-0}" != "1" ]]; then
  run_step "Start Redis" bash "${ROOT}/scripts/run_redis.sh"
else
  echo "Skipping Redis startup (SKIP_REDIS=1)"
fi
run_step "Start backend" bash "${ROOT}/scripts/run_backend.sh"
if [[ "${SKIP_CELERY:-0}" != "1" ]]; then
  run_step "Start Celery worker" bash "${ROOT}/scripts/run_celery_worker.sh"
  run_step "Start Celery beat" bash "${ROOT}/scripts/run_celery_beat.sh"
else
  echo "Skipping Celery worker/beat (SKIP_CELERY=1)"
fi

# check Celery logs for Redis connection or permission errors
sleep 10
if grep -Eiq 'PermissionError|[Cc]onnection.*[Rr]edis' "${LOG_DIR}/celery_worker.err.log" "${LOG_DIR}/celery_beat.err.log"; then
  echo "Celery startup failed due to Redis connection or permission error" >&2
  kill $(cat "${LOG_DIR}/celery_worker.pid" 2>/dev/null) $(cat "${LOG_DIR}/celery_beat.pid" 2>/dev/null) 2>/dev/null || true
  exit 1
fi
run_step ".NET build and app" bash "${ROOT}/scripts/run_net.sh"
run_step "Start frontend" bash "${ROOT}/scripts/run_frontend.sh"
run_step "Start Ollama" bash "${ROOT}/scripts/run_ollama.sh"

echo "All components started successfully."
