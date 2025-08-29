#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common.sh"

OUT_LOG="${LOG_DIR}/install_deps.out.log"
ERR_LOG="${LOG_DIR}/install_deps.err.log"
exec >"${OUT_LOG}" 2>"${ERR_LOG}"

PLATFORM=""
case "$(uname)" in
  Linux*)
    PLATFORM="linux"
    ;;
  CYGWIN*|MINGW*|MSYS*)
    PLATFORM="windows"
    ;;
  *)
    die "Unsupported platform: $(uname)"
    ;;
 esac

REQUIRED_CMDS=(dotnet python3 node npm redis-server celery ollama)

# Allow a simplified mode where Redis/Celery are skipped
if [[ "${SKIP_REDIS:-0}" == "1" ]]; then
  REQUIRED_CMDS=(dotnet python3 node npm celery ollama)
fi
if [[ "${SKIP_CELERY:-0}" == "1" ]]; then
  # Celery is installed via pip in the backend requirements; a system binary is not required
  if [[ "${SKIP_REDIS:-0}" == "1" ]]; then
    REQUIRED_CMDS=(dotnet python3 node npm ollama)
  else
    REQUIRED_CMDS=(dotnet python3 node npm redis-server ollama)
  fi
fi

declare -A LINUX_PKGS=(
  [dotnet]=dotnet-sdk-8.0
  [python3]=python3
  [node]=nodejs
  [npm]=npm
  [redis-server]=redis-server
  [celery]=celery
  [ollama]=ollama
)

declare -A WINDOWS_PKGS=(
  [dotnet]=Microsoft.DotNet.SDK.8
  [python3]=Python.Python.3
  [node]=OpenJS.NodeJS
  [npm]=OpenJS.NodeJS
  # Use Memurai on Windows as a Redis-compatible server
  [redis-server]=Memurai.Memurai
  [celery]=celery
  [ollama]=ollama
)

# On Windows, Memurai installs as a Windows service, not a 'redis-server' binary.
# Treat presence of the service as satisfying the 'redis-server' dependency.
memurai_service_present() {
  if [[ "$PLATFORM" != windows ]]; then return 1; fi
  powershell.exe -NoProfile -Command "if (Get-Service Memurai -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }" \
    >/dev/null 2>&1
}

install_cmd() {
  local cmd="$1" pkg
  # Pre-check: allow Memurai service to satisfy 'redis-server' on Windows
  if [[ "$PLATFORM" == windows && "$cmd" == 'redis-server' ]] && memurai_service_present; then
    log "Memurai service found (satisfies redis-server)"
    return
  fi

  if have_cmd "$cmd"; then
    log "$cmd already installed"
    return
  fi
  log "$cmd not found. Attempting install"
  if [[ "$PLATFORM" == linux ]]; then
    pkg="${LINUX_PKGS[$cmd]:-$cmd}"
    for attempt in 1 2 3; do
      if have_cmd "$cmd"; then break; fi
      apt-get update -y >/dev/null 2>&1 || true
      apt-get install -y "$pkg" >/dev/null 2>&1 || true
    done
  else
    pkg="${WINDOWS_PKGS[$cmd]:-$cmd}"
    for attempt in 1 2 3; do
      if have_cmd "$cmd"; then break; fi
      if have_cmd winget; then
        winget install -e --id "$pkg" -h >/dev/null 2>&1 || true
      elif have_cmd choco; then
        choco install -y "$pkg" >/dev/null 2>&1 || true
      else
        log "No package manager found to install $cmd"
        break
      fi
    done
  fi
  # Post-check: either the command exists or Memurai service satisfies redis-server on Windows
  if have_cmd "$cmd"; then return; fi
  if [[ "$PLATFORM" == windows && "$cmd" == 'redis-server' ]] && memurai_service_present; then
    log "Memurai service is present after install attempts"
    return
  fi
  die "Required command '$cmd' not installed"
}

for cmd in "${REQUIRED_CMDS[@]}"; do
  install_cmd "$cmd"
done

log "All dependencies installed"
