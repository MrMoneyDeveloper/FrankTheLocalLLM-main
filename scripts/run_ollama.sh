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

is_ollama_up() {
  # Prefer HTTP probe
  if command -v curl >/dev/null 2>&1; then
    if curl -sS --max-time 1 http://127.0.0.1:11434/ >/dev/null 2>&1; then
      return 0
    fi
  fi
  # Windows fallback: PowerShell TCP connect
  case "$(uname)" in
    CYGWIN*|MINGW*|MSYS*)
      powershell.exe -NoProfile -Command "try { $c=New-Object Net.Sockets.TcpClient; $c.Connect('127.0.0.1',11434); $ok=$c.Connected; $c.Dispose(); if ($ok) { exit 0 } else { exit 1 } } catch { exit 1 }" \
        >/dev/null 2>&1 && return 0 || true
      ;;
  esac
  # lsof on Unix
  if command -v lsof >/dev/null 2>&1; then
    lsof -ti tcp:11434 >/dev/null 2>&1 && return 0
  fi
  # netstat generic fallback
  netstat -an 2>/dev/null | grep -E "[:\.]11434\s" >/dev/null 2>&1 && return 0 || true
  return 1
}

if is_ollama_up; then
  echo "Ollama already running on 11434; skipping startup" | tee -a "${STAT_LOG}"
  exit 0
fi

log "Starting ollama serve"
ollama serve >>"${OUT_LOG}" 2>>"${ERR_LOG}" &
echo $! > "${LOG_DIR}/ollama.pid"

sleep 5
{ curl -fsS http://127.0.0.1:11434 >>"${PING_LOG}" 2>&1; } || true

log "Ollama running on port 11434"
