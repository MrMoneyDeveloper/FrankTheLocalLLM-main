#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common.sh"

OUT_LOG="${LOG_DIR}/redis.out.log"
ERR_LOG="${LOG_DIR}/redis.err.log"
PING_LOG="${LOG_DIR}/redis_ping.log"
exec >"${OUT_LOG}" 2>"${ERR_LOG}"

# Helpers: test if Redis is reachable without depending on redis-cli
is_redis_up() {
  if command -v redis-cli >/dev/null 2>&1; then
    local out
    out=$(redis-cli -h 127.0.0.1 -p 6379 ping 2>/dev/null || true)
    [[ "${out}" == "PONG" ]]
  elif [[ "$(uname)" =~ CYGWIN|MINGW|MSYS ]]; then
    powershell.exe -NoProfile -Command "try { $c=New-Object Net.Sockets.TcpClient; $c.Connect('127.0.0.1',6379); $ok=$c.Connected; $c.Dispose(); if ($ok) { exit 0 } else { exit 1 } } catch { exit 1 }" \
      >/dev/null 2>&1
  else
    # Fallback: try a TCP connect via bash /dev/tcp if available
    (echo > /dev/tcp/127.0.0.1/6379) >/dev/null 2>&1
  fi
}

# Record initial ping output
: >"${PING_LOG}"
if is_redis_up; then
  echo "Redis already reachable on 6379" | tee -a "${PING_LOG}"
else
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

  # Second reachability attempt after starting service
  if ! is_redis_up; then
    echo "Redis ping failed after restart" | tee -a "${PING_LOG}"
    exit 1
  fi
fi

log "Redis is running on port 6379"
