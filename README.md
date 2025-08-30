# FrankTheLocalLLM — Lite (Python‑Only, Local‑Only)

Local notes + retrieval with Ollama, FastAPI, Gradio, and a persistent Chroma store. No .NET, no Node/Vue, no Redis/Celery, no cloud. Runs fully offline after first model pulls.

## What’s Included
- FastAPI backend: chat, ingest, search
- Gradio UI: chat + vector search
- Ollama for LLM and embeddings (defaults: `llama3.1`, `nomic-embed-text`)
- Persistent Chroma index under `lite/data/chroma`
- First‑run bootstrap: verifies Ollama, pulls models, creates folders
- Port cleanup or auto‑increment to avoid conflicts

## Quick Start
- Start Ollama: `ollama serve`
- Optional first pull: `ollama pull llama3.1` and `ollama pull nomic-embed-text`
- Run the app
  - Windows PowerShell: `./scripts/run.ps1`
  - Linux/macOS: `bash ./scripts/run.sh`

## One-Command Launcher: `runall`
- Cross-platform convenience wrappers are provided at repo root:
  - Unix/Git Bash: `./runall`
  - Windows PowerShell: `./runall.ps1`
- What `runall` does:
  - Creates/activates `.venv` and installs `lite/requirements.txt`
  - Ensures `lite/.env` exists (copies from `.env.example`)
  - Starts Ollama locally if it’s not already running
  - Boots the backend and UI; opens your browser to the UI tab automatically

## UI and API
- UI: http://127.0.0.1:7860 (auto‑increments if busy)
- Health: http://127.0.0.1:8001/health (auto‑increments if busy)
- Chat: `POST /chat` with `{ "prompt": "..." }`
- Search: `GET /search?q=...&k=5`
- Ingest text: `POST /ingest` (multipart file)

## Configuration
- Copy `lite/.env.example` to `lite/.env` to override defaults
- Notable vars: `APP_PORT`, `CHAT_MODEL`, `EMBED_MODEL`, `CHROMA_DIR`, `DATA_DIR`, `UI_PORT`

## Packaging (Windows .exe)
- After a successful run:
  - `./.venv/Scripts/pip install pyinstaller`
  - `./.venv/Scripts/pyinstaller --onefile --name LocalLLM-lite lite/src/launcher.py`
  - Output: `dist/LocalLLM-lite.exe`

## Repo Layout
- `lite/` – Python code and env
- `scripts/run.ps1`, `scripts/run.sh` – single‑command launcher
