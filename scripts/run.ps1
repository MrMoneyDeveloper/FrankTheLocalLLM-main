$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

if (!(Test-Path ".venv")) { python -m venv .venv }
& .\.venv\Scripts\python -m pip install -U pip
& .\.venv\Scripts\pip install -r lite\requirements.txt

if (!(Test-Path "lite\.env")) { Copy-Item "lite\.env.example" "lite\.env" }

# Check ollama
$ollama = (Get-Command "ollama" -ErrorAction SilentlyContinue)
if (-not $ollama) { Write-Error "ollama not found. Install from https://ollama.com and run 'ollama serve'."; exit 1 }

# Run single process (API + UI)
& .\.venv\Scripts\python -m lite.src.launcher

