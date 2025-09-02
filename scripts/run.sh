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

# Ollama (optional) — allow skipping via SKIP_OLLAMA=1
if [ "${SKIP_OLLAMA:-0}" != "1" ]; then
  if ! command -v ollama >/dev/null 2>&1; then
    echo "ERROR: 'ollama' not found. Install from https://ollama.com, or set SKIP_OLLAMA=1" >&2
    exit 1
  fi
  if ! curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    echo "Starting Ollama (serve) in background..."
    ( ollama serve >/dev/null 2>&1 & ) || true
    for i in $(seq 1 40); do
      if curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
        break
      fi
      sleep 0.5
    done
  fi
else
  export FAKE_EMBED=1
  export FAKE_LLM=1
fi

# If Node is available, install deps and run Electron + API together
if command -v node >/dev/null 2>&1; then
  echo "Installing Node dependencies..."
  npm install
  (cd electron && npm install)
  echo "Starting Electron + FastAPI (npm run dev)..."
  npm run dev
else
  echo "Node.js not found; starting Python backend + Gradio UI only"
  python -m lite.src.launcher
fi
