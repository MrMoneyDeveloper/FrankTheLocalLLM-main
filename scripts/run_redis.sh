#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common.sh"

OUT_LOG="${LOG_DIR}/redis.out.log"
ERR_LOG="${LOG_DIR}/redis.err.log"
exec >"${OUT_LOG}" 2>"${ERR_LOG}"

log "Starting Redis"
case "$(uname)" in
  Linux*)
    systemctl start redis-server || true
    ;;
  CYGWIN*|MINGW*|MSYS*)
    powershell.exe -Command "Start-Service redis" || true
    ;;
  *)
    die "Unsupported platform"
    ;;
esac

for i in {1..30}; do
  if { command -v redis-cli >/dev/null 2>&1 && redis-cli -p 6379 ping >/dev/null 2>&1; } || \
     { command -v nc >/dev/null 2>&1 && nc -z localhost 6379 >/dev/null 2>&1; }; then
    log "Redis is running on port 6379"
    exit 0
  fi
  sleep 1
done

die "Redis did not start"
