# FrankTheLocalLLM — Lite (Python-Only backend + Local-Only)

Local notes + retrieval with Ollama, FastAPI, and a persistent Chroma store. Optional Gradio UI and a new Electron desktop app. No cloud. Runs fully offline after first model pulls.

## What's Included
- FastAPI backend: chat, ingest, search, plus notes/groups/settings APIs
- Electron desktop app: tabs, groups, mini-hub, keyword + LLM search
- Gradio UI (optional): chat + vector search
- Ollama for LLM and embeddings (defaults: `llama3.1`, `nomic-embed-text`)
- Persistent Chroma index under `lite/data/chroma`
- First-run bootstrap: verifies Ollama, pulls models, creates folders
- Port cleanup or auto-increment to avoid conflicts

## Quick Start (One Command)
- Start Ollama: `ollama serve`
- Then run the launcher (sets up venv, installs deps, ensures .env, starts backend + UI):
  - Windows: `./runall.ps1`
  - macOS/Linux: `./runall`

## Manual Setup & Run
- Start Ollama: `ollama serve`
- Install Python deps and launch backend + UI:
  - Windows PowerShell: `./scripts/run.ps1`
  - Linux/macOS: `bash ./scripts/run.sh`
- Optional: Start the Electron app (desktop UI):
  - `cd electron && npm install && npm run start`

## One-Command Launcher: `runall`
- Cross-platform convenience wrappers are provided at repo root:
  - Unix/Git Bash: `./runall`
  - Windows PowerShell: `./runall.ps1`
- What `runall` does:
  - Creates/activates `.venv` and installs `lite/requirements.txt`
  - Ensures `lite/.env` exists (copies from `.env.example`)
  - Starts Ollama locally if it's not already running
  - Boots the backend and UI; opens your browser to the UI tab automatically

## UI and API
- Gradio UI (optional): http://127.0.0.1:7860 (auto-increments if busy)
- Electron UI: `electron/` app (uses the FastAPI backend)
- Health: http://127.0.0.1:8001/health (auto-increments if busy)
- Chat: `POST /chat` with `{ "prompt": "..." }`
- RAG Search: `GET /search?q=...&k=5&note_ids=...&group_ids=...&date_start=...&date_end=...`
- Ingest text: `POST /ingest` (multipart file)
- Notes: `GET /notes/list`, `GET /notes/get?id=...`, `POST /notes/create`, `POST /notes/update`, `POST /notes/delete?id=...`
- Groups: `GET /groups/list`, `POST /groups/create`, `POST /groups/delete?id=...`, `POST /groups/add_note?group_id=...&note_id=...`, `POST /groups/remove_note?group_id=...&note_id=...`
- Settings: `GET /settings/get`, `POST /settings/update`

## Configuration
- Copy `lite/.env.example` to `lite/.env` to override defaults
- Notable vars: `APP_PORT`, `CHAT_MODEL`, `EMBED_MODEL`, `CHROMA_DIR`, `DATA_DIR`, `UI_PORT`
- Electron reads `APP_HOST`/`APP_PORT` to reach the backend, or will attempt to spawn the backend using your Python.

## Packaging (Windows .exe)

Two options depending on which UI you want to ship:

- Python (FastAPI + Gradio UI) single-file exe:
  - `./.venv/Scripts/pip install pyinstaller`
  - `./.venv/Scripts/pyinstaller --onefile --name LocalLLM-lite lite/src/launcher.py`
  - Output: `dist/LocalLLM-lite.exe`

- Electron desktop app (optional):
  - Install packager: `cd electron && npm i -D electron-packager`
  - Build: `npx electron-packager . FrankLocalNotes --platform=win32 --arch=x64 --out dist-electron --overwrite`
  - Output folder: `electron/dist-electron/FrankLocalNotes-win32-x64`

## Repo Layout
- `lite/` — Python code and env
- `electron/` — Electron desktop app (preload exposes `window.api`)
- `scripts/run.ps1`, `scripts/run.sh` — single-command launcher

## Tests (placeholder)
- Playwright tests can be added under `electron/tests` for:
  - note creation, group membership, tab operations
  - keyword vs. LLM search scopes
  - crash recovery (autosave snapshots)
