
# FrankTheLocalLLM

This repository contains a minimal front‑end built with Vue.js and Tailwind CSS plus a FastAPI backend and a .NET console application.
FrankTheLocalLLM combines a Vue.js + Tailwind front‑end with a FastAPI backend and a small .NET console application. The frontend is bundled with ESBuild, a minimalist and extremely fast bundler and minifier. It demonstrates how to run a local language‑model driven notes app with background processing and optional desktop packaging.

## Quick Start

Clone the repository and launch everything with a single command. The wrapper
script boots all services via `frank_up.sh` and cleans up with `frank_down.sh`
when you exit. The bootstrap script currently targets Ubuntu or WSL environments,
so other operating systems require a different setup:

```bash
./run_all.sh
```

If the system Python is outdated, upgrade `pip` beforehand to avoid modification errors:

```bash
python -m pip install --upgrade pip
```

You can also manage the stack manually:

```bash
./frank_up.sh   # start services
./frank_down.sh # stop services
```

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

`run_all.sh` delegates to `frank_up.sh` which installs dependencies and launches

the FastAPI backend, Celery worker and Vue.js front‑end. All output and any
errors from the bring‑up process are written to `logs/run_all.log` for
troubleshooting.

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
2. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
3. Run the server:
   ```bash
   python -m backend.app.main
   ```

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
server is reachable on `localhost:6379` and launch the worker and beat processes:

```bash
celery -A backend.app.tasks worker
celery -A backend.app.tasks beat
```
The worker schedules a nightly digest summarizing new chunks and maintains
wiki-style backlinks between notes.

### Importing Data

Upload a ZIP archive to `/api/import` containing Markdown or PDF files. The
server extracts each document, splits it by headings, de-duplicates chunks and
queues embedding jobs in Celery. Vectors are stored in a local Chroma index.



## Testing
Run `scripts/test_pipeline.sh` to lint frontend code, run vitest and pytest suites and apply SQL migrations in a container. If Docker is not available the migration step is skipped.
Run `scripts/test_pipeline.sh` to lint and test the codebase.
