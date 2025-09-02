$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

if (!(Test-Path ".venv")) { python -m venv .venv }
& .\.venv\Scripts\python -m pip install -U pip
& .\.venv\Scripts\pip install -r lite\requirements.txt

if (!(Test-Path "lite\.env")) { Copy-Item "lite\.env.example" "lite\.env" }

# Ollama (optional). Skip with $env:SKIP_OLLAMA=1
if ($env:SKIP_OLLAMA -ne "1") {
  $ollama = (Get-Command "ollama" -ErrorAction SilentlyContinue)
  if (-not $ollama) { Write-Error "ollama not found. Install from https://ollama.com (or set SKIP_OLLAMA=1)"; exit 1 }
  function Test-Ollama {
    try { Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -UseBasicParsing -TimeoutSec 2 | Out-Null; return $true } catch { return $false }
  }
  if (-not (Test-Ollama)) {
    Write-Host "Starting Ollama (serve) in background...)"
    Start-Process -WindowStyle Minimized -NoNewWindow -FilePath "ollama" -ArgumentList "serve" | Out-Null
    $retries = 40
    while ($retries -gt 0) {
      if (Test-Ollama) { break }
      Start-Sleep -Milliseconds 500
      $retries -= 1
    }
  }
} else {
  $env:FAKE_EMBED = "1"; $env:FAKE_LLM = "1"
}

# If Node is present, install deps and run Electron + API via npm
if (Get-Command node -ErrorAction SilentlyContinue) {
  Write-Host "Installing Node dependencies..."
  npm install
  Push-Location electron
  npm install
  Pop-Location
  Write-Host "Starting Electron + FastAPI (npm run dev)..."
  npm run dev
} else {
  Write-Host "Node.js not found; starting Python backend + Gradio UI only"
  & .\.venv\Scripts\python -m lite.src.launcher
}
