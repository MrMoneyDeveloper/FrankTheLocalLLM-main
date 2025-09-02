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
- Start Ollama: `ollama serve` (if it's already running, skip this; a "Only one usage of each socket address" message just means it's already running)
- Then run the launcher (sets up venv, installs deps, ensures .env, starts backend + UI):
  - Windows PowerShell: `./runall.ps1`
  - Windows Git Bash or macOS/Linux: `./runall`

## Manual Setup & Run
- Start Ollama: `ollama serve` (don’t prefix with `bash`; it’s a native executable)
- Install Python deps and launch backend + UI:
  - Windows PowerShell: `./scripts/run.ps1`
  - Windows Git Bash / Linux / macOS: `bash ./scripts/run.sh`
- Optional: Start the Electron app (desktop UI):
  - `cd electron && npm install && npm run start`

## Electron + FastAPI (Dev, Concurrent)
- Install Node deps (root + electron):
  - `npm install`
  - `cd electron && npm install`
- Install Python deps: `pip install -r lite/requirements.txt`
- Start both together:
  - `npm run dev`
  - API: http://127.0.0.1:8001 (auto-increments if busy)
  - Electron loads local `renderer/index.html`; no external network assets

## Debug Logs
- Enable verbose logs by setting `DEBUG=1` before starting:
  - Git Bash / Linux / macOS: `DEBUG=1 ./runall` (or `DEBUG=1 bash ./scripts/run.sh`)
  - PowerShell: `$env:DEBUG='1'; ./runall.ps1` (or `./scripts/run.ps1`)
- Logs are written to your Electron userData path:
  - Windows: `%AppData%/Frank Local Notes/logs/app.log`
  - macOS: `~/Library/Application Support/Frank Local Notes/logs/app.log`
  - Linux: `~/.config/Frank Local Notes/logs/app.log`
- The log captures:
  - Backend spawn and health checks
  - Renderer console messages and failed loads
  - IPC events for open/focus/close
  - Backend stdout/stderr (when DEBUG=1)

## Run Scripts (Updated)
- `./runall` (Unix/Git Bash) or `./runall.ps1` (PowerShell) now:
  - Create `.venv`, install `lite/requirements.txt`
  - Ensure `lite/.env` exists
  - Optionally start Ollama (skip with `SKIP_OLLAMA=1`)
  - Install Node deps at repo root and in `electron/`
  - Start Electron + FastAPI together using `npm run dev`
- You can still run only the Python backend + Gradio UI with `bash ./scripts/run.sh` or `./scripts/run.ps1` if Node isn’t installed.

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

## Detailed Specification

### Objective
Build a local-only Notepad++-style notes application with unlimited tabs, groups, keyword + LLM (RAG) search, per-note mini-hub, autosave/recovery, and tunable performance settings. Front-end: Electron + plain JS + local Bootstrap. Backend: existing Python FastAPI from this repo (keep `/chat`, `/search`, `/ingest`) plus thin new endpoints for notes/groups/settings and Parquet/text storage. No cloud dependencies.

### High-Level Requirements

- Unlimited Notes & Tabs: create/open/manage many notes; each note appears in its own tab; single-open policy focuses an existing tab (no duplicates); tab stacks (merge/unstack) to group tabs (planned).
- Grouping & Organization: create/rename/delete groups; drag-and-drop across/out of groups; multi-group membership; persist stable ordering for groups and notes within groups.
- Two-Mode Search: keyword search across All/Group/This Note with title + snippet; LLM (RAG) search via Python with scope (note/groups/all) and optional date range; return answer + citations.
- Mini-Hub Sidebar: quick actions (Move, Duplicate, Open window); in-note search (prev/next); LLM scope + date pickers + Run; indexing status + Reindex now.
- Settings & Performance: editable model names, chunk size/overlap, reindex debounce, search throttle, max chunks/query; changes persist and apply dynamically (no restart).
- Autosave & Recovery: debounced autosave; snapshot history for undo/redo; on startup, offer recovery if newer snapshot exists.
- Storage & Execution: fully local; notes as text/Markdown; Parquet metadata/embeddings with atomic write (.tmp → fsync → rename) and `.bak` backup.

### Architecture & Boundaries

- UI (Electron + JS): rendering, tabs/stacks, group DnD, mini-hub, settings, autosave, keyword search (may be JS in-memory), and calling backend APIs.
- Backend (Python FastAPI): keep `/chat`, `/search`, `/ingest`; extend with thin endpoints to manage notes/groups/settings; Python handles chunking, embedding, similarity.
- IPC/HTTP: Electron `preload` exposes `window.api.*` methods that call FastAPI via `fetch`.

### Suggested File Layout (guideline)

```
app/
  main/            # Electron main
  preload/         # contextBridge exposing window.api
  renderer/        # index.html + JS modules (Bootstrap local)
  storage/         # (Python) file + Parquet utils
  llm/             # (Python) chunking/embeddings/similarity
  parquet/         # Parquet datasets (written by Python)
    groups.parquet
    group_notes.parquet
    tabs.parquet
    notes_index.parquet
    embeddings.parquet
  notes/           # *.md note files (id.md with front-matter)
  settings/settings.json
  assets/bootstrap # local Bootstrap files
```

### Backend — Keep + Extend FastAPI

Keep:
- `POST /chat` → `{ prompt, allowed_note_ids?, allowed_group_ids?, from_ts?, to_ts? }` → `{ answer, citations[] }`
- `GET /search?q=...` semantic/vector search
- `POST /ingest` for bulk ingestion

Add thin endpoints (Python handles atomic writes + indexing):
- `POST /notes/create` → `{ title, content }` → `{ note_id }`
- `POST /notes/update` → `{ note_id, title?, content? }` → `{ updated_at, hash }` (trigger reindex debounce)
- `POST /notes/delete` → `{ note_id }` (soft delete + cleanup)
- `GET /notes/list` → list from `notes_index.parquet`
- `GET /notes/get?note_id=...` → `{ title, content, updated_at }`
- `POST /groups/create` → `{ name }` → `{ group_id }`
- `POST /groups/rename` → `{ group_id, name }`
- `POST /groups/delete` → `{ group_id }`
- `POST /groups/add_note` → `{ group_id, note_id, position? }`
- `POST /groups/remove_note` → `{ group_id, note_id }`
- `GET /groups/list` → groups with counts/positions
- `GET /groups/notes?group_id=...` → ordered notes in group
- `POST /tabs/save_session` → persist tab order/stacks (optional)
- `GET /tabs/load_session` → restore
- `GET /settings/get` → current config
- `POST /settings/update` → apply: OLLAMA_URL, CHAT_MODEL, EMBED_MODEL, CHUNK_SIZE, OVERLAP, INDEX_DEBOUNCE_MS, SEARCH_THROTTLE_MS, MAX_CHUNKS_PER_QUERY (hot-reload timers)

### Storage Contracts (Parquet)

- `notes_index.parquet`: `note_id`, `title`, `path`, `updated_at:int64`, `size:int64`, `sha256`
- `groups.parquet`: `group_id`, `name`, `created_at`, `updated_at`, `position:int32`
- `group_notes.parquet`: `group_id`, `note_id`, `position:int32`, `added_at`
- `tabs.parquet`: `session_id`, `tab_id`, `note_id`, `stack_id?`, `position:int32`, `created_at`
- `embeddings.parquet`: `note_id`, `chunk_index:int32`, `text`, `embedding:list<float32>`, `updated_at`

Atomic writes: always write `.tmp` → fsync → rename; rotate `.bak`. At startup, validate/repair from `.bak` if needed.

### Electron Preload — API Surface

Expose safe methods (no file paths leaked to renderer):

```
window.api = {
  notes: {
    create({title, content}), update({note_id, title?, content?}), delete({note_id}),
    list(), get({note_id}), open({note_id}), focus({note_id})
  },
  groups: {
    list(), create({name}), rename({group_id, name}), delete({group_id}),
    notes({group_id}), addNote({group_id, note_id, position?}), removeNote({group_id, note_id})
  },
  tabs: {
    merge({tab_ids}), unstack({tab_id}), reorder({new_order}),
    saveSession({session_id}), loadSession({session_id})
  },
  search: {
    keywordAll({q, limit?}), keywordGroup({group_id, q, limit?}), keywordNote({note_id, q})
  },
  llm: { ask({prompt, note_ids?, group_ids?, from_ts?, to_ts?}) },
  settings: { get(), update(partial) }
}
```

### UI Deliverables

- Tabs Bar: drag-reorder; Ctrl/Cmd multi-select with context menu “Merge tabs” (create stack); chevron to switch within stack; close icons.
- Left Sidebar (Groups): list groups with counts; reorder; (+) add; drag notes to assign; “Free Notes” virtual group (notes with no groups).
- Editor Pane: title input (debounced); large textarea; Ctrl+S save; autosave indicator.
- Right Mini-Hub: quick actions, in-note search (highlight + next/prev), LLM scope/date controls, indexing status.
- Global Search (Ctrl+K): modal with tabs [All | Group | This Note]; results open the note at the first match.
- Settings Modal: all performance/LLM fields with validation; apply immediately.

### LLM/RAG Behaviour (Python)

- On note updates: debounce → chunk (size/overlap from settings) → embed via Ollama → replace that note’s rows in `embeddings.parquet` atomically.
- Query: filter allowed `note_id`s by scope/date; load embeddings for allowed notes; cosine similarity + MMR diversity; top-K context into `/chat` system prompt with guardrail “Use ONLY provided context; if not present, reply ‘Not found in allowed scope’.” Return `{answer, citations}`.

### Acceptance Criteria (DoD)

- Notes/Tabs: opening the same note focuses its existing tab; merging/unstacking works; tab order persists across sessions (if saved).
- Groups/DnD: notes can belong to multiple groups; dropping into a group appends at the end; removing from a group doesn’t delete the note.
- Keyword Search: ranked hits with title + snippet in All/Group/Note scopes; case-insensitive; updates after edits.
- LLM Search: with scope=(note|groups|all) and date window, answers use only allowed sources; citations list note titles/excerpts.
- Settings: changing chunk size, debounce, models, etc., affects new indexing/queries without restart.
- Autosave/Recovery: edits survive app crash; on restart, if snapshot is newer than last save, user can recover.
- Local-Only: no internet; Python + Electron communicate via localhost HTTP; all data stored locally as text/Parquet with atomic writes + `.bak`.
- Tests: Playwright (or similar) for create/edit/save, group DnD, tab merge/unstack, keyword scopes, LLM scope/date, single-open, crash recovery.

### Non-Functional

- Startup < 2s on a mid-tier laptop (warm).
- Atomic write operations; recovery uses `.bak` if corruption detected.
- Clear error surfaces in UI (LLM unavailable, embeddings pending, invalid settings).

### Implementation Notes

- Use local Bootstrap assets (no CDN).
- Front-end is plain JS modules; optional small state store permitted.
- Prefer small, composable Python services: `storage/` (text/parquet), `llm/` (chunk/embed/rank), `api/` (routers).
- Strict input validation; renderer never passes raw file paths.

## Core Features & Use Cases

- Unlimited notes and tabs: create, open, and manage multiple notes; single-open policy focuses an existing tab instead of duplicating it.
- Groups and organizing: create groups, drag & drop notes between groups; a note can belong to multiple groups.
- Tab stacks (planned): merge tabs into stacks and unstack them to keep the interface tidy.
- Two-mode search:
  - Keyword search: fast search across all notes, within a single note, or a selected group. Results return title + snippet.
  - LLM (RAG) search: powered by the Python backend. Choose scope (this note, selected groups, or all), optional date range. Returns answers with citations.
- Mini-hub sidebar per note: quick actions (move to group, duplicate, open in new window), in-note search box (prev/next), LLM scope + date pickers with a “Run LLM Search” button, and an indexing status indicator.
- Settings & performance: adjust model names, chunk size/overlap, re-index debounce, search throttle, and max chunks per query. Settings persist and apply dynamically without restarts.
- Autosave & recovery: autosaves after short idle; snapshot history enables undo/redo-like recovery on restart.
- Local-only execution: JS/Electron + Python run fully locally. Storage uses plain text note files and Parquet metadata with atomic writes and backups.

## Backend Integration

- Preserves existing endpoints: `/chat`, `/ingest`, `/search` remain for chat, vector search, and ingestion.
- Adds thin CRUD APIs: `/notes/*`, `/groups/*`, `/settings/*` for note/group management and settings sync; writes notes as text files and metadata as Parquet; triggers re-index as needed.
- Electron to FastAPI: `preload.js` exposes `window.api.notes`, `window.api.groups`, and `window.api.llm` methods that call FastAPI via `fetch`.
- Settings sync: user changes are written to `lite/data/settings.json`; Python reads them dynamically for chunking/embedding/search without restart.
- Module split: Python owns file/Parquet manipulation and embeddings/similarity search; JS/Electron handles UI, tabs, DnD, and editing.

## Collaboration Prompt

Use this prompt to guide contributors or assistants when extending the app:

```
Implement a desktop note‑taking app using Electron + plain JS for the front‑end and our existing Python FastAPI backend (“FrankTheLocalLLM”) for LLM‑powered search and storage. The app must include:

1. Unlimited notes in tabs with a single‑open policy and optional tab stacks (merged tabs).
2. Groups for organizing notes; drag and drop notes between groups; multi‑group membership.
3. Mini‑hub sidebar per note with quick actions, in‑note keyword search, and LLM scope/date filters.
4. Two search modes: (a) fast keyword search across notes or within selected scopes; (b) RAG‑based LLM search via the backend.
5. Autosave, snapshots for undo/redo, and crash recovery.
6. Settings panel to adjust LLM models, chunk size, debounce intervals, search throttle, and max chunks per query.
7. Local storage via text files and Parquet metadata; atomic writes with backup files.
8. FastAPI endpoints for note creation, update, deletion, group management, and settings updates. Use existing `/chat`, `/search`, `/ingest` endpoints for LLM chat, search, and ingestion.
9. Preload script in Electron exposing `window.api` that wraps all HTTP calls.
10. Tests (Playwright or similar) verifying note creation, group membership, tab operations, search scopes, LLM boundary enforcement, and crash recovery.

Focus on modularity: heavy processing (chunking, embeddings, similarity search) lives in Python; the front‑end deals only with UI and high‑level API calls. Everything runs locally without cloud services.
```

## Packaging (Windows .exe)

Two options depending on which UI you want to ship:

- Python (FastAPI + Gradio UI) single-file exe:
  - `./.venv/Scripts/pip install pyinstaller`
  - `./.venv/Scripts/pyinstaller --onefile --name LocalLLM-lite lite/src/launcher.py`
  - Output: `dist/LocalLLM-lite.exe`

- Electron desktop app (optional):
  - Build installers (Win/macOS/Linux):
    - `cd electron && npm run dist`
    - Output under `electron/dist/`
  - Notes:
    - Data directories live under Electron `userData` (e.g., `%AppData%/Frank Local Notes/`), not in the install folder.
    - The Python backend `lite/` is bundled as resources; a system Python is still required unless you ship a PyInstaller exe.

## Troubleshooting
- Ollama port busy (11434): it’s already running. Don’t start it twice; the scripts will detect a running instance.
- On Windows in Git Bash, prefer `./runall` or `bash ./scripts/run.sh`. PowerShell-only scripts (`.ps1`) won’t run directly in Git Bash.
- Gradio UI manifest 404: harmless. Some browsers try `GET /manifest.json`; the app works without it.
- ConnectionResetError 10054 in logs: usually means the browser closed a socket; safe to ignore unless the UI fails to load.

## CI
- GitHub Actions workflow `.github/workflows/ci.yml` runs:
  - Python tests (atomic write + recovery; settings hot-apply)
  - Playwright end-to-end tests (startup, CRUD, groups, tabs, keyword search, LLM search)
- CI runs with `SKIP_OLLAMA=1 FAKE_EMBED=1 FAKE_LLM=1` to avoid external model calls.

## Repo Layout
- `lite/` — Python code and env
- `electron/` — Electron desktop app (preload exposes `window.api`)
- `scripts/run.ps1`, `scripts/run.sh` — single-command launcher

## Tests (placeholder)
- Playwright tests can be added under `electron/tests` for:
  - note creation, group membership, tab operations
  - keyword vs. LLM search scopes
  - crash recovery (autosave snapshots)
