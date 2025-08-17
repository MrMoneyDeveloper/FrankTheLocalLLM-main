#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common.sh"

usage() {
  cat <<'USAGE'
Usage: bash scripts/logs.sh <init|rotate>
  init    - ensure logs/ exists
  rotate  - move *.log to logs/archive/<timestamp>/
USAGE
}

cmd="${1:-init}"
case "${cmd}" in
  init)
    mkdir -p "${LOG_DIR}"
    log "logs initialized at ${LOG_DIR}"
    ;;
  rotate)
    tsdir="${LOG_DIR}/archive/$(date +%Y%m%d-%H%M%S)"
    mkdir -p "${tsdir}"
    shopt -s nullglob
    mv "${LOG_DIR}"/*.log "${tsdir}/" 2>/dev/null || true
    log "rotated logs to ${tsdir}"
    ;;
  *)
    usage
    exit 2
    ;;
esac
