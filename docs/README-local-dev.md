# Local Development Guide

This short guide explains how to run the entire project locally without any packaging step. It is intended for developers who want to test everything from the terminal.

## Prerequisites

- Python 3.11+
- Node.js (for the Vue frontend)
- The .NET 8 SDK (optional but recommended)

## Quick Start

Clone the repository and launch the stack with a single command:

```bash
./run_all.sh
```

The script will:

1. Build and run the .NET console application if `dotnet` is available.
2. Install Python dependencies from `backend/requirements.txt` and start the FastAPI API on port 8001.
3. Install Node dependencies and start the Vue.js Vite dev server on port 5173.
4. Automatically open the UI in your default browser.


Use `./run_logged.sh` to log output to `run.log` while running the same processes and automatically opening the browser.

Press `Ctrl+C` in the terminal to stop all services.

## Manual Steps

If you prefer to run each component manually:

```bash
# Backend
pip install -r backend/requirements.txt
python -m backend.app.main

# Frontend
cd app
npm install
npm run dev

# build a static bundle instead:
npm run build
cd dist
python -m http.server 8080


# .NET console (optional)
dotnet build src/ConsoleAppSolution.sln -c Release
dotnet run --project src/ConsoleApp/ConsoleApp.csproj
```

The default UI is served at `http://localhost:5173` (or `http://localhost:8080` when serving the built bundle).
