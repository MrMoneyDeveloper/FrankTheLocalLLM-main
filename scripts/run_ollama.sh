#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common.sh"

OUT_LOG="${LOG_DIR}/ollama.out.log"
ERR_LOG="${LOG_DIR}/ollama.err.log"

have_cmd ollama || die "ollama not installed"

if ! pgrep -x "ollama" >/dev/null 2>&1; then
  log "Starting ollama serve"
  ollama serve >>"${OUT_LOG}" 2>>"${ERR_LOG}" &
  echo $! > "${LOG_DIR}/ollama.pid"
fi

wait_for_http "http://localhost:11434" 60
log "Ollama running on port 11434"
