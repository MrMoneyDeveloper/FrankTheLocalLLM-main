#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Pick python executable
if command -v python3 >/dev/null 2>&1; then PY=python3; else PY=python; fi

# Create venv if missing
if [ ! -d .venv ]; then
  "$PY" -m venv .venv
fi

# Activate venv (handle Linux/macOS and Git Bash on Windows)
if [ -f .venv/bin/activate ]; then
  # Linux/macOS
  # shellcheck disable=SC1091
  source .venv/bin/activate
elif [ -f .venv/Scripts/activate ]; then
  # Git Bash on Windows
  # shellcheck disable=SC1091
  source .venv/Scripts/activate
else
  echo "ERROR: Could not find venv activate script." >&2
  exit 1
fi

python -m pip install -U pip
python -m pip install -r lite/requirements.txt

# ensure .env
[ -f lite/.env ] || cp lite/.env.example lite/.env

# check ollama
if ! command -v ollama >/dev/null 2>&1; then
  echo "ERROR: 'ollama' not found. Install from https://ollama.com and run 'ollama serve'." >&2
  exit 1
fi

# bootstrap + run single process (API + UI)
python -m lite.src.launcher
