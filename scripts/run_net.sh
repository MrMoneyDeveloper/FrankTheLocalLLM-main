#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common.sh"

OUT_LOG="${LOG_DIR}/dotnet.out.log"
ERR_LOG="${LOG_DIR}/dotnet.err.log"
exec >"${OUT_LOG}" 2>"${ERR_LOG}"

log "Building .NET solution"
dotnet build "${ROOT_DIR}/src/ConsoleAppSolution.sln"

log "Running console application"
dotnet run --project "${ROOT_DIR}/src/ConsoleApp/ConsoleApp.csproj"
