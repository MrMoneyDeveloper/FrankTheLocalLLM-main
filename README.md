
# FrankTheLocalLLM

## Lite: Python‑Only, Local‑Only Mode (Fast start)

This repo now includes a self‑contained Python‑only variant that uses Ollama locally (no .NET, no Node/Vue, no Redis/Celery). It runs offline after the first model pulls, persists to SQLite/FS and Chroma, auto‑handles ports, and can be packaged into a single Windows `.exe`.

What you get:
- FastAPI backend (chat, ingest, search) and Gradio UI
- Ollama for chat and embeddings (default `llama3.1` + `nomic-embed-text`)
- Persistent Chroma index under `lite/data/chroma`
- First‑run bootstrap: verifies Ollama, pulls models, creates folders
- Port cleanup or auto‑increment to avoid conflicts
- Single command to install & run

Quick Start (Lite)
- Install Ollama and start it once in a terminal: `ollama serve`
- Optionally pre‑pull models: `ollama pull llama3.1` and `ollama pull nomic-embed-text`
- Run the app:
  - Windows PowerShell: `./scripts/run.ps1`
  - Linux/macOS: `bash ./scripts/run.sh`

Endpoints and UI
- UI launches on an available port starting at 7860 (e.g. http://127.0.0.1:7860)
- Backend health: http://127.0.0.1:8001/health (auto‑increments if busy)
- Chat: POST http://127.0.0.1:8001/chat {"prompt":"..."}
- Search: GET http://127.0.0.1:8001/search?q=...&k=5
- Ingest: POST http://127.0.0.1:8001/ingest (multipart .txt)

Configuration
- Copy `lite/.env.example` to `lite/.env` to override defaults
- Key vars: `APP_PORT`, `CHAT_MODEL`, `EMBED_MODEL`, `CHROMA_DIR`, `DATA_DIR`

Packaging (Windows .exe)
- From a PowerShell in repo root (after the app has run successfully once):
  - `./.venv/Scripts/pip install pyinstaller`
  - Package the single‑process launcher (starts API + UI):
    `./.venv/Scripts/pyinstaller --onefile --name LocalLLM-lite lite/src/launcher.py`
  - The binary appears under `dist/LocalLLM-lite.exe`

Notes
- The original multi‑stack remains intact; the Lite mode is isolated under `lite/`
- No external services are required. Everything runs locally after initial model pulls.


This repository contains a minimal front‑end built with Vue.js and Tailwind CSS plus a FastAPI backend and a .NET console application.
FrankTheLocalLLM combines a Vue.js + Tailwind front‑end with a FastAPI backend and a small .NET console application. The frontend is bundled with ESBuild, a minimalist and extremely fast bundler and minifier. It demonstrates how to run a local language‑model driven notes app with background processing and optional desktop packaging.

## Quick Start

Clone the repository and launch everything with a single command. The `run_all.sh`
script installs dependencies and starts each component (Redis, .NET, backend,
Celery, front-end and Ollama) in sequence, logging output under `logs/`. On
Windows run it from a Git Bash or WSL shell:

```bash
bash run_all.sh
```

If the system Python is outdated, upgrade `pip` beforehand to avoid modification errors:

```bash
python -m pip install --upgrade pip
```

You can also manage the stack manually with the scripts under `scripts/` or stop
processes using `./frank_down.sh`.

## Features

- Vue front‑end served via a simple HTTP server
- FastAPI API exposing chat, retrieval and import endpoints
- LangChain integration with a local Ollama model
- Background tasks using Celery and Redis
- Example .NET console service with SQLite and Dapper
- File-based Chroma vector store for embeddings
- Devcontainer configuration for offline development

Or clone and launch everything in one step:
```bash
 git clone <repository-url> FrankTheLocalLLM && cd FrankTheLocalLLM && ./run_all.sh
```
## Process Overview

`run_all.sh` orchestrates modular scripts to install dependencies and launch the
FastAPI backend, Celery worker and beat, the Vue.js front‑end, the .NET console
app and Ollama. All output from the orchestration is written to
`logs/run_all.log` for troubleshooting.

1. The Vue front‑end sends requests to the FastAPI backend under `/api`.
2. Notes are chunked and embedded into a Chroma vector store.
3. Retrieval endpoints stream answers from the vector store via LangChain.
4. Background workers summarize entries and maintain backlinks.
5. The optional .NET console app demonstrates additional data access patterns.

## Getting Started
## Documentation


1. Install the Vue.js front-end dependencies and start the ESBuild dev server:
    ```bash
    cd app
    npm install
    npm run dev
    ```
    ESBuild serves the app at `http://localhost:5173` and rebuilds on save.
    To build a static bundle instead:
    ```bash
    npm run build
    cd dist
    node ../server.js
    ```
    then open `http://localhost:8080`.
 - [Local Development Guide](docs/README-local-dev.md) explains how to run everything unpackaged.
 - [Packaging Guide](docs/README-packaging.md) covers building desktop bundles or Docker images.

2. In your browser open the served page. The client expects the FastAPI backend
    to be available at `http://localhost:8001/api`.
    When started the server tries to bind to port `8001` but if it is already
   taken the process automatically increments the port until a free one is
   found. Set the `PORT` environment variable to force a specific port or edit
   `backend/app/config.py`.

    Once the backend is running, the client loads directly into the wiki
    interface without requiring a login.

You can modify `app/index.html` and `app/app.js` to tweak the UI or add new
components.

## Docker Compose Stack

Run the full stack in one shot using Docker Compose and the provided Makefile:

```bash
make dev
```

This launches Postgres, Redis, the FastAPI API plus Celery worker,
an Ollama instance, the Vue front-end and persists a Chroma index. The `dev` target runs database
migrations, seeds a sample Markdown note and opens the UI in your browser.


## Backend API

A simple FastAPI backend is located in the `backend/` directory. The configuration uses environment variables via `pydantic` and enables CORS.

### Setup

1. Install Python 3.11 or newer.
2. Upgrade `pip` and install dependencies:
   ```bash
   python -m pip install --upgrade pip
   pip install -r backend/requirements.txt
   ```
3. Run the server:
   ```bash
   python -m backend.app.main
   ```

When running management commands such as database migrations, invoke them as modules:

```bash
python -m backend.app.manage <command>
```

Executing `manage.py` directly can trigger an "attempted relative import with no known parent package" error.

The server exposes a sample endpoint at `/api/hello` returning a welcome message.

### Trivia Chain Demo

The backend now includes a simple [LangChain](https://python.langchain.com) setup
that uses a local LLM provided by [Ollama](https://ollama.ai). A small knowledge
base lives in `backend/data/trivia.md` and is loaded into a vector store on
startup. When Ollama is running locally, you can query this data via:

```bash
curl "http://localhost:8001/api/trivia?q=What is the largest planet?"
```

Make sure to install the new Python dependencies and have an Ollama model (for
example `llama3`) available.

### Retrieval QA

The `/api/qa/stream` endpoint streams answers from a LangChain RetrievalQA chain
backed by a Chroma index. Results include markdown formatted citations linking to the
original note.


## Console Service

A .NET console application demonstrates SQLite data access using Dapper following a simple clean architecture layout. Projects reside in `src/`.

### Setup

1. Install the .NET SDK 8.0 or newer and verify the version:
   ```bash
   dotnet --version
   ```
   If the runtime loader complains about a different version (for example 9.0.1) install the matching SDK or update the `TargetFramework` in the project files.
2. Restore and build the solution (this also installs NuGet packages if needed):
   ```bash
   dotnet build src/ConsoleAppSolution.sln -c Release
   ```
3. Run the console app:
   ```bash
   dotnet run --project src/ConsoleApp/ConsoleApp.csproj
   ```

If `dotnet restore` warns that vulnerability data cannot be downloaded you can disable the audit by placing a `nuget.config` file next to the solution with:

```xml
<configuration>
  <config>
    <add key="VulnerabilityMode" value="Off" />
  </config>
</configuration>
```

By default the app stores data in `app.db`, creating the database if it does not exist.
The infrastructure project also exposes a `UserRepository` with async CRUD
operations powered by Dapper. Migration scripts under
`src/Infrastructure/Migrations` set up tables for `users`, `entries`, `tasks`
and `llm_logs`. A simple `user_stats` view provides aggregate counts which the
repository surfaces via `GetStatsAsync`.

## Dev Container

A `.devcontainer` configuration is provided for offline development.
It installs Python 3.11, Node.js, the .NET 8 SDK, SQLite and Ollama.
The container mounts a Docker volume at `/root/.ollama` so models and
database files persist between sessions.

Launch the environment with the [devcontainer CLI](https://containers.dev/cli):

```bash
devcontainer up
```

## Running Everything Together

To build and launch all parts of the project at once run:

```bash
./run_all.sh
```

The script sequentially builds the .NET console app, installs Python dependencies, launches the FastAPI API and starts the Vue.js ESBuild dev server on port 5173. Use `./run_logged.sh` to run the same process with output logged to `run.log`. The backend server stops automatically when you exit the dev server.
On Windows run the commands from `run_all.sh` one by one in PowerShell (first `cd app`, then `npm install && npm run dev`) or execute the script in WSL. Running them in order ensures all dependencies are restored.


Background tasks that summarize entries can be started separately. Ensure a Redis
server is running and reachable on `redis://localhost:6379/0`, then launch the worker
and beat processes in separate terminals:

```bash
celery -A backend.app.tasks worker
celery -A backend.app.tasks beat
```
The worker schedules a nightly digest summarizing new chunks and maintains
wiki-style backlinks between notes. On Windows the combined `celery -B` mode is
unsupported; starting the worker and beat separately avoids errors. If the
logs show connection refusals to Redis, ensure the Redis server is running or
update `REDIS_URL` to point to an accessible broker.

### Importing Data

Upload a ZIP archive to `/api/import` containing Markdown or PDF files. The
server extracts each document, splits it by headings, de-duplicates chunks and
queues embedding jobs in Celery. Vectors are stored in a local Chroma index.



## Testing
Run `scripts/test_pipeline.sh` to lint frontend code, run vitest and pytest suites and apply SQL migrations in a container. If Docker is not available the migration step is skipped.
Run `scripts/test_pipeline.sh` to lint and test the codebase.
