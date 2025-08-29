#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 -m venv .venv >/dev/null 2>&1 || true
source .venv/bin/activate

pip install -U pip
pip install -r lite/requirements.txt

# ensure .env
[ -f lite/.env ] || cp lite/.env.example lite/.env

# check ollama
if ! command -v ollama >/dev/null 2>&1; then
  echo "ERROR: 'ollama' not found. Install from https://ollama.com and run 'ollama serve'." >&2
  exit 1
fi

# bootstrap + run single process (API + UI)
python -m lite.src.launcher

