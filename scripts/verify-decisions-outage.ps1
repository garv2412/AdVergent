$ErrorActionPreference='Stop'
. .\scripts\env.ps1
$env:E2E_OPERATOR_PASSWORD=(Get-Content -Raw .runtime/operator-password.txt).Trim()
$phase13Launcher=Join-Path $env:LOCALAPPDATA 'AdVergent\tools\exasol.exe'
$phase13BrowserResult=1
try {
    & $phase13Launcher stop --deployment advergent *> .runtime/phase13-outage-stop.log
    if ($LASTEXITCODE -ne 0) { throw 'Existing Exasol stop failed' }
    Write-Output ('Actual Exasol stop verified at '+[DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromMinutes(330)).ToString('yyyy-MM-dd HH:mm:ss zzz'))
    $env:E2E_DATABASE_FAILURE='1'
    npm.cmd test --prefix frontend -- ads.spec.ts attribution.spec.ts breakout.spec.ts budget.spec.ts clearance.spec.ts cohorts.spec.ts commerce.spec.ts decisions.spec.ts diagnostics.spec.ts finance.spec.ts foundation.spec.ts inventory.spec.ts *> .runtime/phase13-outage.log
    $phase13BrowserResult=$LASTEXITCODE
    Get-Content .runtime/phase13-outage.log -Tail 19
} finally {
    Remove-Item Env:E2E_DATABASE_FAILURE -ErrorAction SilentlyContinue
    & $phase13Launcher start --deployment advergent *> .runtime/phase13-outage-start.log
    if ($LASTEXITCODE -ne 0) { throw 'Existing Exasol start failed' }
    foreach($phase13Command in @('probe','refresh','commerce','ads','attribution','finance','inventory','diagnostics')) {
        & .\.venv\Scripts\python.exe -m advergent.worker $phase13Command
        if ($LASTEXITCODE -ne 0) { throw "Default restoration failed: $phase13Command" }
    }
    $phase13Original=Get-Content -Raw .runtime/phase12-preservation.json | ConvertFrom-Json
    foreach($phase13File in $phase13Original.PSObject.Properties.Name) {
        if ((Get-FileHash -LiteralPath $phase13File -Algorithm SHA256).Hash -ne $phase13Original.$phase13File) {throw 'Preservation hash mismatch'}
    }
    Write-Output 'PASS: five original private/TLS/launcher/deployment/unrelated-file hashes unchanged; existing stores and seven defaults restored'
}
exit $phase13BrowserResult
