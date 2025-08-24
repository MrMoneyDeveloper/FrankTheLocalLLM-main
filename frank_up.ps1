# PowerShell bootstrap for Windows
Set-StrictMode -Version Latest

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$frontDir = Join-Path $Root 'app'

$LogDir  = Join-Path $Root 'logs'
$LogFile = Join-Path $LogDir 'frank_up.log'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
Start-Transcript -Path $LogFile -Append
Write-Output ("=== frank_up.ps1 started at {0} ===" -f (Get-Date))

# Resolve venv binaries explicitly
$venvBin = Join-Path $Root '.venv\Scripts'
$PythonExe = Join-Path $venvBin 'python.exe'
$CeleryExe = Join-Path $venvBin 'celery.exe'

function Need-Cmd ($cmd) { Get-Command $cmd -ErrorAction SilentlyContinue }

function Install-IfMissing ($cmd, $wingetId, $chocoPkg) {
  if (-not (Need-Cmd $cmd)) {
    if (Need-Cmd 'winget') {
      winget install --id $wingetId -e --silent
    } elseif (Need-Cmd 'choco') {
      choco install $chocoPkg -y
    } else {
      Write-Error ("Missing {0} and no package manager found" -f $cmd)
      exit 1
    }
  }
}

function Free-Port($port) {
  try {
    $cons = Get-NetTCPConnection -LocalPort $port -ErrorAction Stop
    $pids = $cons | Select-Object -ExpandProperty OwningProcess -Unique
    if ($pids) {
      Write-Output ("Killing processes on port {0}: {1}" -f $port, ($pids -join ', '))
      foreach ($pid in $pids) { try { Stop-Process -Id $pid -Force } catch {} }
    }
  } catch {
    Write-Output ("No process running on port {0}" -f $port)
  }
}

# Helper to launch a process with separate stdout/stderr logs
function Start-LoggedProcess {
  param(
    [string]$Name,
    [string]$FilePath,
    [string[]]$ArgumentList,
    [string]$WorkingDirectory
  )

  $out = Join-Path $LogDir ("{0}.out.log" -f $Name)
  $err = Join-Path $LogDir ("{0}.err.log" -f $Name)
  Remove-Item $out, $err -ErrorAction SilentlyContinue

  $startInfo = @{ FilePath = $FilePath; RedirectStandardOutput = $out; RedirectStandardError = $err; PassThru = $true }
  if ($ArgumentList) { $startInfo.ArgumentList = $ArgumentList }
  if ($WorkingDirectory) { $startInfo.WorkingDirectory = $WorkingDirectory }

  return Start-Process @startInfo
}

Install-IfMissing git 'Git.Git' 'git'
Install-IfMissing python 'Python.Python.3' 'python'
Install-IfMissing node 'OpenJS.NodeJS.LTS' 'nodejs'
Install-IfMissing redis-server 'Microsoft.OpenSource.Redis' 'redis-64'
Install-IfMissing ollama 'Ollama.Ollama' 'ollama'
Install-IfMissing dotnet 'Microsoft.DotNet.SDK.8' 'dotnet-sdk'

if (Get-Service redis -ErrorAction SilentlyContinue) {
  Start-Service redis
} elseif (Need-Cmd 'redis-server') {
    Start-LoggedProcess -Name 'redis' -FilePath 'redis-server' | Out-Null

}

if (Get-Service ollama -ErrorAction SilentlyContinue) {
  Start-Service ollama
} elseif (Need-Cmd 'ollama') {
  Free-Port 11434
    Start-LoggedProcess -Name 'ollama' -FilePath 'ollama' -ArgumentList 'serve' | Out-Null

}

python -m venv .venv
$activate = [IO.Path]::Combine($Root,'.venv','Scripts','Activate.ps1')
. $activate
& $PythonExe -m pip install --upgrade pip
& $PythonExe -m pip install -r backend/requirements.txt

$envPath = Join-Path $Root '.env'
if (-not (Test-Path $envPath)) {
@'
PORT=8001
DATABASE_URL=sqlite:///./app.db
MODEL=llama3
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
DEBUG=false
'@ | Set-Content $envPath
}

Get-Content $envPath | ForEach-Object {
  $pair = $_.Split('=',2)
  [Environment]::SetEnvironmentVariable($pair[0], $pair[1])
}
$backendPort = [int]([Environment]::GetEnvironmentVariable('PORT'))
if (-not $backendPort) { $backendPort = 8001 }
Free-Port 8000
Free-Port $backendPort


$backend = Start-LoggedProcess -Name 'backend' -FilePath $PythonExe -ArgumentList @('-m','backend.app.main')
if ($backend) {
  $backend.Id | Out-File (Join-Path $LogDir 'backend.pid')
} else {
  Write-Error 'Failed to start backend'
}

for ($i=0; $i -lt 30; $i++) {
  try {
    Invoke-WebRequest -UseBasicParsing ("http://localhost:{0}/api/hello" -f $backendPort) | Out-Null
    break
  } catch {
    Start-Sleep -Seconds 1
  }
}

function Test-Tcp($host, $port, $timeoutSec=3) {
  try { ($c = New-Object Net.Sockets.TcpClient).BeginConnect($host,$port,$null,$null) | Out-Null
        $ok = ($c.Client.Poll($timeoutSec*1000000,[Net.Sockets.SelectMode]::SelectWrite) -or $c.Connected)
        $c.Close(); return $ok } catch { return $false }
}

# Wait for Redis (3 tries)
$redisOk = $false
for ($i=1; $i -le 3; $i++) {
  if (Test-Tcp 'localhost' 6379) { $redisOk = $true; break }
  Write-Warning "Redis not reachable (try $i/3). Attempting restart…"
  if (Get-Service redis -ErrorAction SilentlyContinue) { Restart-Service redis -ErrorAction SilentlyContinue }
  Start-Sleep -Seconds 2
}
if (-not $redisOk) {
  Write-Error "Redis unavailable after 3 tries. Shutting down."
  & "$Root\frank_down.sh"
  exit 1
}

function Test-Ollama($timeoutSec=3) {
  try {
    $resp = Invoke-WebRequest -UseBasicParsing -TimeoutSec $timeoutSec "http://localhost:11434"
    return $resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500
  } catch { return $false }
}

# Ensure Ollama running (3 tries)
$ollamaOk = $false
for ($i=1; $i -le 3; $i++) {
  if (Test-Ollama) { $ollamaOk = $true; break }
  Write-Warning "Ollama not responding (try $i/3). Restarting…"
  if (Get-Service ollama -ErrorAction SilentlyContinue) {
    Restart-Service ollama -ErrorAction SilentlyContinue
  } else {
    Start-Process -FilePath 'ollama' -ArgumentList 'serve' | Out-Null
  }
  Start-Sleep -Seconds 2
}
if (-not $ollamaOk) {
  Write-Error "Ollama failed after 3 tries. Shutting down stack."
  & "$Root\frank_down.sh"
  exit 1
}

if (Test-Path $CeleryExe) {
  $celery = Start-LoggedProcess -Name 'celery_worker' -FilePath $CeleryExe -ArgumentList @('-A','backend.app.tasks','worker')
  if ($celery) {
    $celery.Id | Out-File (Join-Path $LogDir 'celery_worker.pid')
  } else {
    Write-Error 'Failed to start Celery worker'
  }

  $celeryBeat = Start-LoggedProcess -Name 'celery_beat' -FilePath $CeleryExe -ArgumentList @('-A','backend.app.tasks','beat')
  if ($celeryBeat) {
    $celeryBeat.Id | Out-File (Join-Path $LogDir 'celery_beat.pid')
  } else {
    Write-Error 'Failed to start Celery beat'
  }
} else {
  Write-Error 'Celery executable not found in virtual environment'
}

# .NET console app
$dotnet = Start-LoggedProcess -Name 'dotnet' -FilePath 'dotnet' -ArgumentList @('run','--project','src/ConsoleApp/ConsoleApp.csproj')
if ($dotnet) {
  $dotnet.Id | Out-File (Join-Path $LogDir 'dotnet.pid')
} else {
  Write-Error 'Failed to start .NET console app'
}

# Frontend (ESBuild dev server)
$NpmCmd = Join-Path $env:ProgramFiles 'nodejs\npm.cmd'
& $NpmCmd --prefix $frontDir install | Out-Null
$frontend = Start-LoggedProcess -Name 'frontend' -FilePath 'node' -ArgumentList @('esbuild.config.js','--serve') -WorkingDirectory $frontDir
if ($frontend) {
  $frontend.Id | Out-File (Join-Path $LogDir 'frontend.pid')
} else {
  Write-Error 'Failed to start frontend'
}

Write-Output 'OS            : Windows'
Write-Output ("Backend URL   : http://localhost:{0}/api" -f $backendPort)
Write-Output 'Frontend URL  : http://localhost:5173'


Stop-Transcript
