#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
kill_if() { [[ -f "$1" ]] && kill "$(cat "$1")" 2>/dev/null && rm -f "$1"; }

echo "Stopping frontend, backend, celery (and user-session ollama if present)..."
kill_if logs/frontend.pid
kill_if logs/backend.pid
kill_if logs/celery_worker.pid
kill_if logs/celery_beat.pid
kill_if logs/ollama.pid

echo "Done."
