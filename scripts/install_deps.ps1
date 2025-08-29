$ErrorActionPreference = 'Stop'
$required = @('dotnet','python','node','npm','redis-server','celery','ollama')
$pkgs = @{ 
  'dotnet' = 'Microsoft.DotNet.SDK.8'
  'python' = 'Python.Python.3'
  'node' = 'OpenJS.NodeJS'
  'npm' = 'OpenJS.NodeJS'
  # Prefer Memurai on Windows as a Redis-compatible server
  'redis-server' = 'Memurai.Memurai'
  'celery' = 'celery'
  'ollama' = 'ollama'
}

function Install-Cmd($cmd) {
  if (Get-Command $cmd -ErrorAction SilentlyContinue) { return }
  $pkg = $pkgs[$cmd]
  Write-Host "$cmd not found. Attempting install"
  for ($i=0; $i -lt 3; $i++) {
    if (Get-Command $cmd -ErrorAction SilentlyContinue) { break }
    if (Get-Command winget -ErrorAction SilentlyContinue) {
      winget install --id $pkg -e -h | Out-Null
    } elseif (Get-Command choco -ErrorAction SilentlyContinue) {
      choco install $pkg -y | Out-Null
    } else {
      throw "No package manager to install $cmd"
    }
  }
  if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
    throw "Required command $cmd not installed"
  }
}

foreach ($cmd in $required) { Install-Cmd $cmd }
Write-Host 'All dependencies installed'
