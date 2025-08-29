#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common.sh"

OUT_LOG="${LOG_DIR}/redis.out.log"
ERR_LOG="${LOG_DIR}/redis.err.log"
PING_LOG="${LOG_DIR}/redis_ping.log"
exec >"${OUT_LOG}" 2>"${ERR_LOG}"

# Record initial ping output
: >"${PING_LOG}"
if command -v redis-cli >/dev/null 2>&1; then
  PING_RESULT=$(redis-cli -h 127.0.0.1 -p 6379 ping 2>&1 | tee -a "${PING_LOG}")
elif [[ -x "/c/Redis-x64-5.0.14.1/redis-cli.exe" ]]; then
  PING_RESULT=$("/c/Redis-x64-5.0.14.1/redis-cli.exe" -h 127.0.0.1 -p 6379 ping 2>&1 | tee -a "${PING_LOG}")
else
  echo "redis-cli not found" | tee -a "${PING_LOG}"
  PING_RESULT=""
fi

if [[ "${PING_RESULT}" != "PONG" ]]; then
  log "Redis ping failed, attempting to start service"
  case "$(uname)" in
    Linux*)
      systemctl start redis-server || true
      ;;
    CYGWIN*|MINGW*|MSYS*)
      powershell.exe -Command "Start-Service Memurai" || \
      powershell.exe -Command "Start-Service RedisLocal" || \
      powershell.exe -Command "Start-Service redis" || true
      ;;
    *)
      die "Unsupported platform"
      ;;
  esac
  sleep 2

  # Second ping attempt after starting service
  if command -v redis-cli >/dev/null 2>&1; then
    PING_RESULT=$(redis-cli -h 127.0.0.1 -p 6379 ping 2>&1 | tee -a "${PING_LOG}")
  elif [[ -x "/c/Redis-x64-5.0.14.1/redis-cli.exe" ]]; then
    PING_RESULT=$("/c/Redis-x64-5.0.14.1/redis-cli.exe" -h 127.0.0.1 -p 6379 ping 2>&1 | tee -a "${PING_LOG}")
  else
    PING_RESULT=""
  fi

  if [[ "${PING_RESULT}" != "PONG" ]]; then
    echo "Redis ping failed after restart" | tee -a "${PING_LOG}"
    exit 1
  fi
fi

log "Redis is running on port 6379"
