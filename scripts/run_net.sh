#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common.sh"

OUT_LOG="${LOG_DIR}/dotnet.out.log"
ERR_LOG="${LOG_DIR}/dotnet.err.log"
exec >"${OUT_LOG}" 2>"${ERR_LOG}"

DB_FILE="${ROOT_DIR}/app.db"
APP_FILE="${ROOT_DIR}/app"
if [[ -f "${APP_FILE}" || -f "${DB_FILE}" ]]; then
  log "Removing stale SQLite DB ..."
  rm -f "${APP_FILE}" "${DB_FILE}"
fi

log "Building .NET solution"
dotnet build "${ROOT_DIR}/src/ConsoleAppSolution.sln"

log "Running console application"
dotnet run --project "${ROOT_DIR}/src/ConsoleApp/ConsoleApp.csproj" --configuration Release

# Detect schema mismatch error
if grep -q 'NOT NULL constraint failed: entries.title' "${ERR_LOG}" 2>/dev/null; then
  log "Schema mismatch detected in .NET console output"
  exit 1
fi
