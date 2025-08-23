#!/usr/bin/env bash
set -eEuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

LOG_DIR="$ROOT/logs"
LOG_FILE="$LOG_DIR/run_all.log"
mkdir -p "$LOG_DIR"
export LOG_FILE

exec > >(tee -a "$LOG_FILE") 2>&1
echo "=== run_all.sh started at $(date) ==="

# Determine supported platform (Ubuntu/WSL or Windows)
case "$(uname)" in
  Linux*)
    if [[ -r /etc/os-release ]] && grep -qi ubuntu /etc/os-release; then
      PLATFORM="ubuntu"
    else
      echo "This bootstrap currently supports Ubuntu and Windows."
      exit 0
    fi
    ;;
  CYGWIN*|MINGW*|MSYS*)
    PLATFORM="windows"
    ;;
  *)
    echo "This bootstrap currently supports Ubuntu and Windows."
    exit 0
    ;;
esac

# Relaunch with sudo if not running as root on Ubuntu. If sudo is unavailable continue
if [[ $PLATFORM == "ubuntu" && $EUID -ne 0 ]]; then
  if command -v sudo >/dev/null 2>&1; then
    echo "This script requires administrative privileges. Re-running with sudo..."
    exec sudo "$0" "$@"
  else
    echo "Warning: running without root privileges" >&2
  fi
fi

free_port() {
  local port=$1
  if command -v lsof >/dev/null 2>&1 && lsof -ti tcp:"$port" >/dev/null 2>&1; then
    lsof -ti tcp:"$port" | xargs kill -9 >/dev/null 2>&1 || true
  fi
}

cleanup() {
  if [[ -z "${CLEANED_UP:-}" ]]; then
    CLEANED_UP=1
    "$ROOT/frank_down.sh"
    free_port 5173
    free_port 8001
    free_port 11434
  fi
}

error_handler() {
  local exit_code=$?
  echo "Error on line $1: $2 (exit code $exit_code)" >&2
  exit "$exit_code"
}

trap cleanup EXIT
trap 'error_handler ${LINENO} "$BASH_COMMAND"' ERR

run_step() {
  local desc="$1"; shift
  echo "--- $desc ---"
  "$@"
}

# Ensure Yarn is available and install dependencies via workspaces
if ! command -v yarn >/dev/null 2>&1; then
  run_step "Yarn not found. Installing globally" npm install -g yarn
fi
run_step "Installing workspace dependencies with Yarn" bash -c "cd '$ROOT' && yarn install"

run_step "Building .NET console application" bash -c "dotnet build '$ROOT/src/ConsoleAppSolution.sln' -c Release 2>&1 | tee '$LOG_DIR/dotnet-build.log'"

echo "--- Building Python backend ---"
if [[ $PLATFORM == "windows" ]]; then
  PYTHON_BIN="python"
  VENV_ACTIVATE="$ROOT/.venv/Scripts/activate"
else
  PYTHON_BIN="python3"
  VENV_ACTIVATE="$ROOT/.venv/bin/activate"
fi
run_step "Preparing Python environment" bash -c "[ -d '$ROOT/.venv' ] || $PYTHON_BIN -m venv '$ROOT/.venv'"
# shellcheck disable=SC1090
run_step "Installing backend dependencies" bash -c "source '$VENV_ACTIVATE' && pip install --upgrade pip && pip install -r '$ROOT/backend/requirements.txt' && $PYTHON_BIN -m backend.app.manage migrate 2>&1 | tee -a '$LOG_DIR/backend-build.log'"

if [[ $PLATFORM == "ubuntu" ]]; then
  run_step "Running frank_up.sh" "$ROOT/frank_up.sh"

  run_step "Installing frontend dependencies" npm --prefix "$ROOT/app" install
  start_frontend() {
    node "$ROOT/app/esbuild.config.js" --serve >"$LOG_DIR/frontend.out.log" 2>"$LOG_DIR/frontend.err.log" &
    echo $! > "$LOG_DIR/frontend.pid"
  }
  run_step "Starting ESBuild dev server" start_frontend
else
  run_step "Running frank_up.ps1" powershell.exe -ExecutionPolicy Bypass -File "$ROOT/frank_up.ps1"
fi

echo "Logs directory: $LOG_DIR (backend.log, frontend.out.log, frontend.err.log, dotnet.log, etc.)"

# Verify backend dev server is responding
echo "--- Checking backend availability ---"
backend_up=""
for i in {1..15}; do
  if curl -fsS http://localhost:8001/api/hello >/dev/null 2>&1; then
    echo "Backend responding on http://localhost:8001"
    backend_up=1
    break
  fi
  sleep 1
done
if [[ -z $backend_up ]]; then
  echo "Backend not responding on http://localhost:8001" >&2
  exit 1
fi

# Verify Celery worker and beat are running
for pid_file in "$LOG_DIR/celery_worker.pid" "$LOG_DIR/celery_beat.pid"; do
  if [[ ! -s $pid_file ]] || ! kill -0 "$(cat "$pid_file")" >/dev/null 2>&1; then
    echo "Required Celery process missing: $pid_file" >&2
    exit 1
  fi
done

# Verify frontend dev server is responding
echo "--- Checking frontend availability ---"
frontend_up=""
for i in {1..15}; do
  if curl -fsS http://localhost:5173 >/dev/null 2>&1; then
    echo "Frontend responding on http://localhost:5173"
    frontend_up=1
    break
  fi
  sleep 1
done
if [[ -z $frontend_up ]]; then
  echo "Frontend not responding on http://localhost:5173. See $LOG_DIR/frontend.out.log and $LOG_DIR/frontend.err.log" >&2
fi

# Helper to open the default browser on the correct platform
open_browser() {
  local url="http://localhost:5173"
  case "$(uname)" in
    Darwin*) cmd="open" ;;
    CYGWIN*|MINGW*|MSYS*) cmd="cmd.exe /c start" ;;
    *) cmd="xdg-open" ;;
  esac

  if command -v ${cmd%% *} >/dev/null 2>&1; then
    $cmd "$url" >/dev/null 2>&1 &
  else
    echo "Please open $url in your browser." >&2
  fi
}

launch_tauri() {
  if command -v cargo >/dev/null 2>&1; then
    (cd "$ROOT/tauri" && cargo tauri dev >/dev/null 2>&1 &)
  else
    echo "cargo not found; defaulting to browser." >&2
    open_browser
  fi
}

echo "Services are running. Choose how to view the UI:"
echo "1) Open http://localhost:5173 in your browser"
echo "2) Run the Tauri desktop app"
if [[ -t 0 ]]; then
  read -rp "Selection [1/2]: " choice
else
  choice=1
  echo "Non-interactive shell detected; defaulting to 1 (browser)."
fi

case "$choice" in
  2)
    echo "Launching Tauri app..."
    launch_tauri
    ;;
  *)
    echo "Opening browser..."
    open_browser
    ;;
esac

echo "Press Ctrl+C to stop services."
while true; do
  sleep 1 || break
done
