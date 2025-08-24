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
  [redis-server]=Redis.Redis
  [celery]=celery
  [ollama]=ollama
)

install_cmd() {
  local cmd="$1" pkg
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
  have_cmd "$cmd" || die "Required command '$cmd' not installed"
}

for cmd in "${REQUIRED_CMDS[@]}"; do
  install_cmd "$cmd"
done

log "All dependencies installed"
