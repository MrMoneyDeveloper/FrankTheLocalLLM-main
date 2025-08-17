#!/usr/bin/env bash
set -euo pipefail

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


error_handler() {
  local exit_code=$?
  echo "Error on line $1: $2 (exit code $exit_code)" >&2
}
trap 'error_handler ${LINENO} "$BASH_COMMAND"' ERR
trap "$ROOT/frank_down.sh" EXIT



if [[ $PLATFORM == "ubuntu" ]]; then
  echo "--- Running frank_up.sh ---"
  "$ROOT/frank_up.sh"
else
  echo "--- Running frank_up.ps1 ---"
  powershell.exe -ExecutionPolicy Bypass -File "$ROOT/frank_up.ps1"
fi


# Ensure Vite is installed for the frontend
echo "--- Ensuring Vite is installed ---"
if ! npm --prefix app ls vite >/dev/null 2>&1; then
  echo "Vite not found. Attempting installation..."
  set +e
  npm --prefix app install vite
  vite_status=$?
  set -e
  if [[ $vite_status -ne 0 ]]; then
    echo "Vite installation failed. Check logs for details." >&2
  elif ! npm --prefix app ls vite >/dev/null 2>&1; then
    echo "Vite still missing after installation attempt." >&2
  else
    echo "Vite installation confirmed."
  fi
else
  echo "Vite already installed."
fi

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
  echo "Frontend not responding on http://localhost:5173. See logs/frontend.log" >&2
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

