#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common.sh"

OUT_LOG="${LOG_DIR}/ollama.out.log"
ERR_LOG="${LOG_DIR}/ollama.err.log"
STAT_LOG="${LOG_DIR}/ollama.log"
PING_LOG="${LOG_DIR}/ollama_ping.log"

have_cmd ollama || die "ollama not installed"

: >"${PING_LOG}"
: >"${STAT_LOG}"

# Skip startup if Ollama already responds on the default port (any HTTP status is fine)
if curl -sS --max-time 1 http://127.0.0.1:11434/ >/dev/null 2>&1; then
  echo "Ollama API already responding on 11434; skipping startup" | tee -a "${STAT_LOG}"
  exit 0
fi

# Secondary check using lsof when available (Linux/macOS)
if command -v lsof >/dev/null 2>&1; then
  if lsof -ti tcp:11434 >/dev/null 2>&1; then
    echo "Port 11434 already in use, skipping Ollama startup" | tee -a "${STAT_LOG}"
    exit 0
  fi
fi

log "Starting ollama serve"
ollama serve >>"${OUT_LOG}" 2>>"${ERR_LOG}" &
echo $! > "${LOG_DIR}/ollama.pid"

sleep 5
{ curl -fsS http://127.0.0.1:11434 >>"${PING_LOG}" 2>&1; } || true

log "Ollama running on port 11434"
