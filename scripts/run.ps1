$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

if (!(Test-Path ".venv")) { python -m venv .venv }
& .\.venv\Scripts\python -m pip install -U pip
& .\.venv\Scripts\pip install -r lite\requirements.txt

if (!(Test-Path "lite\.env")) { Copy-Item "lite\.env.example" "lite\.env" }

# Check/start ollama
$ollama = (Get-Command "ollama" -ErrorAction SilentlyContinue)
if (-not $ollama) { Write-Error "ollama not found. Install from https://ollama.com"; exit 1 }

# If Ollama API not responding, start server
function Test-Ollama {
  try { Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -UseBasicParsing -TimeoutSec 2 | Out-Null; return $true } catch { return $false }
}
if (-not (Test-Ollama)) {
  Write-Host "Starting Ollama (serve) in background..."
  Start-Process -WindowStyle Minimized -NoNewWindow -FilePath "ollama" -ArgumentList "serve" | Out-Null
  # Wait up to ~20s
  $retries = 40
  while ($retries -gt 0) {
    if (Test-Ollama) { break }
    Start-Sleep -Milliseconds 500
    $retries -= 1
  }
}

# Run single process (API + UI)
& .\.venv\Scripts\python -m lite.src.launcher
