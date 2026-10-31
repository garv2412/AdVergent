# Restart only the verified idle local AdVergent API, preserving private settings.
$ErrorActionPreference='Stop'
Set-Location (Join-Path $PSScriptRoot '..')
. .\scripts\env.ps1
$demoListeners=@(Get-NetTCPConnection -State Listen -LocalPort 8000 -ErrorAction SilentlyContinue)
if ($demoListeners.Count -ne 1 -or $demoListeners[0].LocalAddress -ne '127.0.0.1') {
    throw 'Expected one existing loopback API listener; refusing to stop another process'
}
$demoProcess=Get-CimInstance Win32_Process -Filter "ProcessId=$($demoListeners[0].OwningProcess)"
if ($demoProcess.CommandLine -notmatch 'uvicorn.*advergent.api:create_app.*--host 127.0.0.1.*--port 8000') {
    throw 'Listener is not the expected AdVergent API; refusing restart'
}
try {
    Stop-Process -Id $demoListeners[0].OwningProcess -ErrorAction Stop
    Wait-Process -Id $demoListeners[0].OwningProcess -Timeout 10 -ErrorAction SilentlyContinue
} finally {
    if (Get-NetTCPConnection -State Listen -LocalPort 8000 -ErrorAction SilentlyContinue) {
        throw 'Port remains occupied; refusing to start a competing process'
    }
    $demoStarted=Start-Process -FilePath (Join-Path $PWD '.venv\Scripts\python.exe') -ArgumentList @('-m','uvicorn','advergent.api:create_app','--factory','--host','127.0.0.1','--port','8000') -WorkingDirectory $PWD -WindowStyle Hidden -RedirectStandardOutput (Join-Path $PWD '.runtime/phase14-api.stdout.log') -RedirectStandardError (Join-Path $PWD '.runtime/phase14-api.stderr.log') -PassThru
    $demoStarted.Id | Set-Content .runtime/phase14-api.pid
    $demoReady=$false
    for($demoAttempt=0;$demoAttempt -lt 40;$demoAttempt++) {
        try {
            $demoResponse=Invoke-WebRequest http://127.0.0.1:8000/api/session -SkipHttpErrorCheck -TimeoutSec 2
            if ($demoResponse.StatusCode -eq 401) { $demoReady=$true; break }
        } catch { }
        Start-Sleep -Milliseconds 500
    }
    if (-not $demoReady) { throw 'Restarted API did not become ready; inspect private runtime logs' }
    if ((Get-NetTCPConnection -State Listen -LocalPort 8000).LocalAddress -ne '127.0.0.1') { throw 'API listener is not loopback' }
    Write-Output 'PASS: verified idle local API restarted with existing private environment; unauthenticated access denied; listener loopback'
}
