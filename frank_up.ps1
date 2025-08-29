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
$venvScripts = Join-Path (Join-Path $Root '.venv') 'Scripts'
$PythonExe = Join-Path $venvScripts 'python.exe'
$CeleryExe = Join-Path $venvScripts 'celery.exe'

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
  [CmdletBinding()]
  param(
    [Parameter(Mandatory)] [string]$Name,
    [Parameter(Mandatory)] [string]$FilePath,
    [string[]]$ArgumentList,
    [string]$WorkingDirectory,
    [switch]$SingleLog
  )

  $out = Join-Path $LogDir ("{0}.out.log" -f $Name)
  $err = Join-Path $LogDir ("{0}.err.log" -f $Name)
  Remove-Item $out, $err -ErrorAction SilentlyContinue

  if ($SingleLog.IsPresent) {
    # Start-Process cannot redirect both streams to the same file.
    # Use a wrapper PowerShell command to merge all streams.
    $log = Join-Path $LogDir ("{0}.log" -f $Name)
    Remove-Item $log -ErrorAction SilentlyContinue

    $quotedExe = '"' + $FilePath + '"'
    $argsText = if ($ArgumentList -and $ArgumentList.Length -gt 0) {
      ($ArgumentList | ForEach-Object { if ($_ -match '\s' -or $_ -match '"') { '"' + ($_ -replace '"','\"') + '"' } else { $_ } }) -join ' '
    } else { '' }
    $cmd = if ($argsText) { "& $quotedExe $argsText *>> '" + $log + "' 2>&1" } else { "& $quotedExe *>> '" + $log + "' 2>&1" }

    $psi = @{ FilePath = 'powershell'; ArgumentList = @('-NoLogo','-NoProfile','-Command', $cmd); PassThru = $true }
    if ($WorkingDirectory) { $psi.WorkingDirectory = $WorkingDirectory }
    return Start-Process @psi
  }

  $startInfo = @{ FilePath = $FilePath; RedirectStandardOutput = $out; RedirectStandardError = $err; PassThru = $true }
  if ($ArgumentList) { $startInfo.ArgumentList = $ArgumentList }
  if ($WorkingDirectory) { $startInfo.WorkingDirectory = $WorkingDirectory }

  return Start-Process @startInfo
}

# Helper: dump last N lines of process logs
function Show-ProcessLogs {
  param(
    [Parameter(Mandatory)] [string]$Name,
    [int]$Lines = 200
  )
  $out = Join-Path $LogDir ("{0}.out.log" -f $Name)
  $err = Join-Path $LogDir ("{0}.err.log" -f $Name)
  if (Test-Path $out) {
    Write-Output ("---- {0} stdout (last {1}) ----" -f $Name, $Lines)
    Get-Content $out -Tail $Lines | Write-Output
  }
  if (Test-Path $err) {
    Write-Output ("---- {0} stderr (last {1}) ----" -f $Name, $Lines)
    Get-Content $err -Tail $Lines | Write-Output
  }
}

# Lightweight TCP test (declared early so we can use it before other definitions)
function Test-Tcp($hostname, $port){
  try {
    $c = New-Object Net.Sockets.TcpClient
    $c.Connect($hostname,$port)
    $c.Dispose()
    return $true
  } catch { return $false }
}

Install-IfMissing git 'Git.Git' 'git'
Install-IfMissing python 'Python.Python.3' 'python'
Install-IfMissing node 'OpenJS.NodeJS.LTS' 'nodejs'
Install-IfMissing ollama 'Ollama.Ollama' 'ollama'
Install-IfMissing dotnet 'Microsoft.DotNet.SDK.8' 'dotnet-sdk'


$redisExe = Join-Path $env:ProgramFiles 'Redis\redis-server.exe'
$redisService = $null
if (Get-Service redis -ErrorAction SilentlyContinue) {
  $redisService = 'redis'
} elseif (Get-Service RedisLocal -ErrorAction SilentlyContinue) {
  $redisService = 'RedisLocal'
}

if ($redisService) {
  Start-Service $redisService
} elseif (Test-Path $redisExe) {
  Start-LoggedProcess -Name 'redis' -FilePath $redisExe | Out-Null
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
if (-not $backend) {
  Write-Error 'Failed to start backend'
  Show-ProcessLogs -Name 'backend' -Lines 200
  & "$Root\frank_down.sh"
  exit 1
}

# Immediately write PID and verify the process exists
$backendPid = $backend.Id
$backendPid | Out-File (Join-Path $LogDir 'backend.pid')
Start-Sleep -Milliseconds 200
if (-not (Get-Process -Id $backendPid -ErrorAction SilentlyContinue)) {
  Write-Error 'Backend process is not running right after start.'
  Show-ProcessLogs -Name 'backend' -Lines 200
  & "$Root\frank_down.sh"
  exit 1
}

# Gate on TCP readiness to avoid noisy HTTP errors
$tcpReady = $false
for ($i=1; $i -le 20; $i++) {
  if (Test-Tcp 'localhost' $backendPort) { $tcpReady = $true; break }
  if (-not (Get-Process -Id $backendPid -ErrorAction SilentlyContinue)) {
    Write-Error 'Backend process exited before opening TCP port.'
    Show-ProcessLogs -Name 'backend' -Lines 200
    & "$Root\frank_down.sh"
    exit 1
  }
  Start-Sleep -Milliseconds 500
}
if (-not $tcpReady) {
  Write-Error ("Backend TCP port {0} did not open in time." -f $backendPort)
  Show-ProcessLogs -Name 'backend' -Lines 200
  & "$Root\frank_down.sh"
  exit 1
}

# Hardened HTTP health probe with short timeouts
$httpOk = $false
for ($i=1; $i -le 20; $i++) {
  try {
    Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 ("http://localhost:{0}/api/hello" -f $backendPort) | Out-Null
    $httpOk = $true
    break
  } catch {
    if (-not (Get-Process -Id $backendPid -ErrorAction SilentlyContinue)) {
      Write-Error 'Backend process exited during HTTP health check.'
      Show-ProcessLogs -Name 'backend' -Lines 200
      & "$Root\frank_down.sh"
      exit 1
    }
    Start-Sleep -Seconds 1
  }
}
if (-not $httpOk) {
  Write-Error 'Backend HTTP health check failed after 20 attempts.'
  Show-ProcessLogs -Name 'backend' -Lines 200
  & "$Root\frank_down.sh"
  exit 1
}

function Test-Port($hostname, $port){ try{ (New-Object Net.Sockets.TcpClient).Connect($hostname,$port) ; return $true } catch { return $false } }

# Wait for Redis (3 tries)
$redisOk = $false
for ($i=1; $i -le 3; $i++) {
    if (Test-Port 'localhost' 6379) { $redisOk = $true; break }
    Write-Warning "Redis not reachable (try $i/3). Restarting..."
    if ($redisService -and (Get-Service $redisService -ErrorAction SilentlyContinue)) {
        Restart-Service $redisService -ErrorAction SilentlyContinue
    } elseif (Test-Path $redisExe) {
        Start-LoggedProcess -Name 'redis' -FilePath $redisExe | Out-Null
    }
    Start-Sleep -Seconds 2
}
if (-not $redisOk) {
    Write-Error "Redis unavailable after 3 tries"
    & "$Root\frank_down.sh"
    exit 1
}

function Test-Ollama() {
    try {
        (Invoke-WebRequest -UseBasicParsing "http://localhost:11434" -TimeoutSec 3) | Out-Null
        return $true
    }
    catch { return $false }
}

# Ensure Ollama running (3 tries)
$ollamaOk = $false
for ($i=1; $i -le 3; $i++) {
    if (Test-Ollama) { $ollamaOk = $true; break }
    Write-Warning "Ollama not responding (try $i/3). Restarting…"
    if (Get-Service ollama -ErrorAction SilentlyContinue) {
        Restart-Service ollama -ErrorAction SilentlyContinue
    } else {
        Start-LoggedProcess -Name 'ollama' -FilePath 'ollama' -ArgumentList 'serve' | Out-Null
    }
    Start-Sleep -Seconds 2
}

# If still not responding, attempt reinstall once via winget
if (-not $ollamaOk) {
    Write-Warning "Ollama still not responding. Attempting reinstall..."
    Start-Process winget -ArgumentList 'install --id=Ollama.Ollama -e --silent' -Wait
    Start-LoggedProcess -Name 'ollama' -FilePath 'ollama' -ArgumentList 'serve' | Out-Null
    Start-Sleep -Seconds 5
    if (Test-Ollama) { $ollamaOk = $true }
}

if (-not $ollamaOk) {
    Write-Error "Ollama unavailable after reinstall attempt. Shutting down."
    & "$Root\frank_down.sh"
    exit 1
}

if (Test-Path $CeleryExe) {
  # Celery worker (force solo pool on Windows)
  $celery = Start-LoggedProcess -Name 'celery_worker' -FilePath $CeleryExe -ArgumentList @('-A','backend.app.tasks','worker','--pool=solo')
  if (-not $celery) {
    Write-Error 'Failed to start Celery worker'
  } else {
    $celeryPid = $celery.Id
    Start-Sleep -Milliseconds 200
    if (Get-Process -Id $celeryPid -ErrorAction SilentlyContinue) {
      $celeryPid | Out-File (Join-Path $LogDir 'celery_worker.pid')
    } else {
      Write-Error 'Celery worker process exited immediately after start'
      Show-ProcessLogs -Name 'celery_worker' -Lines 200
    }
  }

  # Celery beat
  $celeryBeat = Start-LoggedProcess -Name 'celery_beat' -FilePath $CeleryExe -ArgumentList @('-A','backend.app.tasks','beat')
  if (-not $celeryBeat) {
    Write-Error 'Failed to start Celery beat'
  } else {
    $celeryBeatPid = $celeryBeat.Id
    Start-Sleep -Milliseconds 200
    if (Get-Process -Id $celeryBeatPid -ErrorAction SilentlyContinue) {
      $celeryBeatPid | Out-File (Join-Path $LogDir 'celery_beat.pid')
    } else {
      Write-Error 'Celery beat process exited immediately after start'
      Show-ProcessLogs -Name 'celery_beat' -Lines 200
    }
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

# Frontend (Vite dev server) with separate logs + guards
$NpmCmd = Join-Path $env:ProgramFiles 'nodejs\npm.cmd'
& $NpmCmd --prefix $frontDir install | Out-Null
$frontend = Start-LoggedProcess -Name 'frontend' -FilePath $NpmCmd -ArgumentList @('run','dev') -WorkingDirectory $frontDir
if (-not $frontend) {
  Write-Error 'Failed to start frontend'
} else {
  $frontendPid = $frontend.Id
  Start-Sleep -Milliseconds 200
  if (Get-Process -Id $frontendPid -ErrorAction SilentlyContinue) {
    $frontendPid | Out-File (Join-Path $LogDir 'frontend.pid')
  } else {
    Write-Error 'Frontend process exited immediately after start'
    Show-ProcessLogs -Name 'frontend' -Lines 200
  }
}

Write-Output 'OS            : Windows'
Write-Output ("Backend URL   : http://localhost:{0}/api" -f $backendPort)
Write-Output 'Frontend URL  : http://localhost:5173'


Stop-Transcript
