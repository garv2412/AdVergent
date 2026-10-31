# Existing local deployment only. Never install, bootstrap, reset, prune or remove.
$ErrorActionPreference='Stop'
Set-Location (Join-Path $PSScriptRoot '..')
. .\scripts\env.ps1
$env:E2E_OPERATOR_PASSWORD=(Get-Content -Raw .runtime/operator-password.txt).Trim()
$demoLauncher=Join-Path $env:LOCALAPPDATA 'AdVergent\tools\exasol.exe'
$demoBrowserResult=1
$demoContainers=@('advergent-postgres','exasol-db-71bd4e63')
$demoMounts=@{}
foreach($demoContainer in $demoContainers) {
    $demoMounts[$demoContainer]=(& podman inspect $demoContainer --format '{{json .Mounts}}')
    if ($LASTEXITCODE -ne 0) { throw 'Existing container inspection failed; refusing recovery' }
}
if ($env:E2E_DATABASE_FAILURE) { throw 'Begin recovery from healthy mode' }
try {
    # Stop/start the existing PostgreSQL container, retaining its named volume.
    try {
        & podman stop advergent-postgres *> .runtime/phase14-postgres-stop.log
        if ($LASTEXITCODE -ne 0) { throw 'Existing PostgreSQL stop failed' }
        & .\.venv\Scripts\python.exe -c "from advergent.config import Settings; from advergent.operational import OperationalStore; from sqlalchemy.exc import SQLAlchemyError; s=OperationalStore(Settings.from_env().database_url); failed=False; exec('try:\n s.publication()\nexcept SQLAlchemyError:\n failed=True'); assert failed, 'PostgreSQL still reachable'"
        if ($LASTEXITCODE -ne 0) { throw 'Actual PostgreSQL outage not confirmed' }
    } finally {
        & podman start advergent-postgres *> .runtime/phase14-postgres-start.log
        if ($LASTEXITCODE -ne 0) { throw 'Existing PostgreSQL restart failed' }
    }
    & $demoLauncher stop --deployment advergent *> .runtime/phase14-exasol-stop.log
    if ($LASTEXITCODE -ne 0) { throw 'Existing Exasol stop failed' }
    & .\.venv\Scripts\python.exe -c "from advergent.config import Settings; from advergent.exasol import ExasolAnalytics; from advergent.contracts import AnalyticsUnavailable; failed=False; exec('try:\n ExasolAnalytics(Settings.from_env()).probe()\nexcept AnalyticsUnavailable:\n failed=True'); assert failed, 'Exasol still reachable'"
    if ($LASTEXITCODE -ne 0) { throw 'Actual Exasol outage not confirmed' }
    Write-Output ('Actual preserving outages verified at '+[DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromMinutes(330)).ToString('yyyy-MM-dd HH:mm:ss zzz'))
    $env:E2E_DATABASE_FAILURE='1'
    npm.cmd test --prefix frontend -- ads.spec.ts attribution.spec.ts breakout.spec.ts budget.spec.ts clearance.spec.ts cohorts.spec.ts commerce.spec.ts decisions.spec.ts demo.spec.ts diagnostics.spec.ts finance.spec.ts foundation.spec.ts inventory.spec.ts *> .runtime/phase14-outage.log
    $demoBrowserResult=$LASTEXITCODE
    Get-Content .runtime/phase14-outage.log -Tail 20
} finally {
    Remove-Item Env:E2E_DATABASE_FAILURE -ErrorAction SilentlyContinue
    & $demoLauncher start --deployment advergent *> .runtime/phase14-exasol-start.log
    if ($LASTEXITCODE -ne 0) { throw 'Existing Exasol restart failed' }
    foreach($demoCommand in @('probe','refresh','commerce','ads','attribution','finance','inventory','diagnostics')) {
        & .\.venv\Scripts\python.exe -m advergent.worker $demoCommand
        if ($LASTEXITCODE -ne 0) { throw "Default restoration failed: $demoCommand" }
    }
    foreach($demoContainer in $demoContainers) {
        $demoAfterMounts=(& podman inspect $demoContainer --format '{{json .Mounts}}')
        if ($LASTEXITCODE -ne 0 -or $demoAfterMounts -ne $demoMounts[$demoContainer]) { throw 'Existing persistent mount changed' }
    }
    & .\.venv\Scripts\python.exe scripts/verify-demo-state.py
    if ($LASTEXITCODE -ne 0) { throw 'Final preservation/analytical audit failed' }
    Write-Output 'PASS: existing PostgreSQL/Exasol mounts reused; defaults, private/TLS files, observations and action history preserved'
}
exit $demoBrowserResult
