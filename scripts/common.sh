#!/usr/bin/env bash
set -Eeuo pipefail

# ---- logging ----
ts() { date +"%Y-%m-%d %H:%M:%S"; }
log() { printf "[%s] %s\n" "$(ts)" "$*" >&2; }
die() { printf "[%s] ERROR: %s\n" "$(ts)" "$*" >&2; exit 1; }

# ---- env ----
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${ROOT_DIR}/logs"
mkdir -p "${LOG_DIR}"

have_cmd() { command -v "$1" >/dev/null 2>&1; }


init_logs() { mkdir -p "${LOG_DIR}"; }

rotate_logs() {
  local tsdir="${LOG_DIR}/archive/$(date +%Y%m%d-%H%M%S)"
  mkdir -p "${tsdir}"
  shopt -s nullglob
  mv "${LOG_DIR}"/*.log "${tsdir}/" 2>/dev/null || true
  log "rotated logs to ${tsdir}"
}


# ---- port helpers (Git Bash + Windows safe) ----
free_port() {
  local port="${1:?port required}"
  if have_cmd lsof; then
    lsof -ti "tcp:${port}" | xargs -r -I{} kill -9 {} || true
  else
    local pids
    pids=$(netstat -ano 2>/dev/null | grep ":${port} " | awk '{print $5}' | sort -u || true)
    if [[ -n "${pids}" ]]; then
      while read -r pid; do
        [[ -z "${pid}" || "${pid}" == "0" ]] && continue
        taskkill //PID "${pid}" //F >/dev/null 2>&1 || true
      done <<< "${pids}"
    fi
  fi
  sleep 0.2
}

# ---- HTTP readiness ----
wait_for_http() {
  local url="${1:?url}"; local timeout="${2:-60}"
  local start end
  start=$(date +%s)
  while true; do
    if curl -fsS --max-time 2 "${url}" >/dev/null 2>&1; then return 0; fi
    end=$(date +%s)
    if (( end - start >= timeout )); then
      die "Timed out waiting for ${url}"
    fi
    sleep 1
  done
}

# ---- venv ----
ensure_venv() {
  local venv="${ROOT_DIR}/.venv"
  if [[ ! -x "${venv}/Scripts/python.exe" && ! -x "${venv}/bin/python" ]]; then
    log "Creating venv at ${venv}"
    python -m venv "${venv}" || die "venv creation failed"
  fi
  # shellcheck disable=SC1091
  source "${venv}/Scripts/activate" 2>/dev/null || \
  source "${venv}/bin/activate" 2>/dev/null || die "failed to activate venv"
}

open_browser() {
  local url="${1:?url}"
  if have_cmd cmd.exe; then
    cmd.exe /c start "" "$url" >/dev/null 2>&1 || true
  elif have_cmd xdg-open; then
    xdg-open "$url" >/dev/null 2>&1 || true
  fi
}
