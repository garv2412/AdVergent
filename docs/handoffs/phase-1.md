# Phase 1 handoff

Date: 2026-10-27. Status: **complete for the accepted local foundation slice; exit gate met**. This chat implements Phase 1 only. Earlier progress notes below are preserved and superseded by the final execution evidence.

## Changes and deliverables

- [Setup guide](../phase-1-setup.md), [Python project](../../pyproject.toml) and [dependency lock](../../requirements-lock.txt).
- [API](../../backend/advergent/api.py), [typed contracts](../../backend/advergent/contracts.py), [PostgreSQL store](../../backend/advergent/operational.py), [migration](../../migrations/001_foundation.sql), [analytics adapter](../../backend/advergent/exasol.py) and [refresh worker](../../backend/advergent/worker.py).
- [Golden input/expected fixture](../../fixtures/foundation-v1.json), [React UI](../../frontend/src/main.tsx), generated OpenAPI/TypeScript contracts and reproducible frontend lockfile/build.
- [Isolated backend checks](../../backend/tests/test_foundation.py), [opt-in real integration checks](../../backend/tests/test_integration.py) and [browser checks](../../frontend/tests/foundation.spec.ts).
- Ignored local config/runtime locations, PostgreSQL startup script/compose alternative, operator configuration and documentation checker. No advertising controls, later-phase modules, live integrations, cloud resources, commits or pushes.

## Decisions and implementation defaults

The user explicitly started Phase 1, reconfirmed AWS Free-plan status, and accepted local whole-application fallback. No updated numeric credit balance was supplied; retain the prior USD 139.73 as historical evidence only. AWS eligibility, IAM/quota and complete resource-cost checks remain unperformed because no CLI/profile was available; no provisioning took place.

The user reported accidentally cancelling the first Podman install and explicitly asked to restart it. The second install succeeded (5.8.3). The pinned Exasol 2.3.0 Windows launcher is outside Git. ZIP hash matches the digest published for that asset on GitHub; Authenticode signature is valid. Correction to the initial install attempt: a PowerShell nonterminating checksum-download failure allowed `version` to run before digest verification; verification subsequently succeeded against the release asset page. No database was deployed before that verification.

React/Vite, FastAPI, PostgreSQL, PyExasol and the two-line foundation fixture are implemented engineering defaults. Financial recognition/threshold defaults remain as previously labelled; this slice does not implement full financial behavior. Golden expectations are INR 4,000 net sales, INR 1,300 contribution before ads and INR 300 after ads, calculated from fixture inputs by the adapter when real Exasol is available.

## Checks and results (October 27, IST)

| Command | Result and limits |
|---|---|
| `git status --short`, repository/document reads | Existing modified README/untracked planning files and user image preserved; no prior application code |
| `Get-Command aws,docker,wsl,exasol,node,npm,python,py,winget,podman,psql -ErrorAction SilentlyContinue`; `node --version`; `python --version`; `wsl --list --verbose` | Node 24.14.0, Python 3.14.3; WSL2 docker-desktop stopped; no AWS CLI/profile, Podman or Exasol at initial inspection |
| `docker info --format '{{.ServerVersion}}'` | Failed: Linux engine pipe unavailable. Attempted hidden Desktop start; engine not established |
| `winget install --id RedHat.Podman --exact --version 5.8.3 --silent --accept-package-agreements --accept-source-agreements --disable-interactivity` | First cancelled (1602), second user-authorized retry succeeded |
| `Get-AuthenticodeSignature ...exasol.exe`; `Get-FileHash ...exasol.zip` against GitHub asset digest | Valid signature; SHA-256 `6300c83528d2f6a7a79a468351564bc75e88004f07b5cf28429be80ff94e6fcf` matches release asset page. Release API was rate-limited; checksum text download failed; asset page resolved |
| `.\.venv\Scripts\python.exe -m pytest -q` | 5 passed, 1 real integration test skipped. Contract tests use store/analytics substitutes except real unreachable-socket error. No real analytical success asserted |
| `.\.venv\Scripts\python.exe scripts/export_openapi.py`; `npm.cmd run types --prefix frontend` | Passed; generated API types |
| `npm.cmd run build --prefix frontend` | Passed TypeScript and Vite production build. Initial native Rollup blocked by Windows Application Control; official WASM Rollup alias/override fixed build |
| `.\.venv\Scripts\python.exe -m pip check`; `.\.venv\Scripts\python.exe -m compileall -q backend scripts` | Passed. Native SQLAlchemy was blocked; supported pure-Python source build succeeded with `DISABLE_SQLALCHEMY_CEXT=1` |
| `.\.venv\Scripts\python.exe scripts/serve-preview.py`; `npm.cmd test --prefix frontend` | 2 browser tests passed, 1 real authenticated Exasol browser test skipped. Uses installed Chrome. Downloaded Chromium could not launch (`spawn UNKNOWN`); no Windows policy disabled. Screenshot inspected: login layout clean at 1280px. Preview config deliberately has unavailable databases |

## Earlier runtime progress (superseded by final evidence below)

Podman WSL image preparation is still running at this update. One premature launcher attempt started a second machine initialization; its child and launcher were stopped, leaving the explicitly sized initializer running. Do not run concurrent machine initialization. Launcher deployment state is outside Git, named `advergent`; initialization does not mean the database is installed.

Actual PostgreSQL/Exasol startup, verified private listeners, certificate-authenticated `SELECT 1`, golden load/query, repeat load and real authenticated UI path have not passed yet. Real integration and operator browser tests are opt-in and currently skipped. No A01–A26 case is marked complete. Rendering substitutions prove UI behavior only. The full A26 interrupted-refresh case is not established by code alone; an integration test exercises rollback after a real duplicate-key failure when enabled.

Only loopback local operation is being prepared. Production login throttling, account management, orphan-dataset cleanup, full finance, source adapters, recommendations and action execution remain absent. There are no live integrations or model-effectiveness claims.

## Earlier remaining-work list (completed below)

1. Complete Podman machine preparation, inspect memory/storage availability and deploy pinned Exasol Personal privately.
2. Configure dedicated database credentials/fingerprint privately, start PostgreSQL, apply migrations and run real probe/refresh/replay/failure tests.
3. Run the real operator browser path, inspect result/failure display, and record exact evidence and any limitations here.
4. Rerun documentation/new-file checks and update status/gate. Do not start Phase 2 until Phase 1 gate is met and the user requests its separate chat.

Schedule: October 27 foundation remains the immediate target; runtime setup determines completion time. Remaining October 28–30 milestones are tight, not guaranteed. No original phase scope is silently merged or waived; deadline remains October 30 at 23:59 IST.

## Final execution evidence and corrections (October 27, approximately 00:49–01:00 IST)

Local deployment is operational and the Phase 1 gate is met. No cloud resources or paid APIs were used. AWS remains conditional/unverified; the accepted whole-application local fallback was used instead.

- Podman CLI 5.8.3 installed; the official 5.8 machine artifact contains server 5.8.9. Initial OCI transfers stalled. A resumable local download used the public Quay manifest's WSL x86-64 blob, then verified SHA-256 `5089400f5586e7bc65505bbf5a4e193374eea681a08a792745d22d73bf75704d` and exact size 248,920,453 bytes. `podman machine init --cpus 2 --memory 4096 --disk-size 30 --image .runtime/podman-machine.x86_64.wsl.tar.zst` and `podman machine start` succeeded. WSL manages actual resource consumption; the requested sizing is not a measured hard cap for all host workloads.
- Confirmed no Exasol process was running, then cleared the interrupted launcher's stale lock with `exasol diag unlock --deployment advergent`. `exasol install local --deployment advergent --ports db:8563` succeeded. Exasol Personal uses bundled `exasol/nano:2026.2.0-nano.3`.
- The local launcher lacks a certificate fingerprint and recommends skipping validation. Instead, `podman cp CONTAINER_NAME:/exa/certificates/fullchain.pem .runtime/exasol-fullchain.pem` obtained the public certificate from the trusted local container. `scripts/bootstrap-exasol.py` derives its fingerprint, reads launcher credentials privately, creates the application user, rotates the admin credential and updates private config. Initial password formatting used an unquoted identifier conversion, which changed case; actual app authentication exposed it. Fixed to quoted case-preserving conversion, corrected both private credentials and verified application login. Neither password nor private key is in repository documents/logs.
- PostgreSQL's larger Debian image download was abandoned before container creation; the delivered configuration uses `postgres:17.9-alpine`. `.\scripts\start-postgres.ps1` succeeded. Observed image digest: `sha256:e19c5d72436d4d2f54d00c789775095d02a5dfb1c0f7ea5a243230b1bb46c2bb`. `podman exec advergent-postgres pg_isready -U advergent -d advergent` succeeded.
- `Get-NetTCPConnection -LocalPort 5432,8563 -State Listen` showed **127.0.0.1 for both**. Container port mappings also show loopback. No public database exposure or hybrid tunnel is configured.

Reproducible verification commands run after `. .\scripts\env.ps1`:

```powershell
.\.venv\Scripts\python.exe -m advergent.worker migrate
.\.venv\Scripts\python.exe -m advergent.worker probe
.\.venv\Scripts\python.exe -m advergent.worker refresh
$env:RUN_INTEGRATION='1'
.\.venv\Scripts\python.exe -m pytest -q
Remove-Item Env:RUN_INTEGRATION
```

**Result: 6 passed, no skips**, including real PostgreSQL and Exasol. Verified exact golden SQL totals; replay stable at two analytical lines; wrong TLS fingerprint rejected; publication retained after a controlled unavailability failure; actual duplicate-primary-key failure after the first INSERT rolled back to zero lines in the incomplete dataset; prior publication unchanged; no running jobs left behind; unauthenticated API denied; real persisted session authorized a metric query and was denied after expiry. The integration test creates two deliberate failed audit jobs; they remain audit evidence, not unresolved failures. A final `refresh` returned the latest state to succeeded. Observed audit counts at closeout: four succeeded, two deliberately failed.

The actual application runs with `.\.venv\Scripts\python.exe -m uvicorn advergent.api:create_app --factory --host 127.0.0.1 --port 8000`. Preview process was stopped. Private operator password is in ignored `.runtime/operator-password.txt`; database credentials are in ignored `.env`, recovery material and launcher state. `git check-ignore` confirmed these private paths are ignored. No secrets were printed into the handoff.

Browser checks used installed Chrome against the real application, with the operator password loaded privately into process environment:

```powershell
$env:E2E_OPERATOR_PASSWORD=[System.IO.File]::ReadAllText((Join-Path $PWD '.runtime/operator-password.txt'))
npm.cmd test --prefix frontend
# Actual outage, not an intercepted response:
& "$env:LOCALAPPDATA\AdVergent\tools\exasol.exe" stop --deployment advergent
$env:E2E_DATABASE_FAILURE='1'
npm.cmd test --prefix frontend
Remove-Item Env:E2E_DATABASE_FAILURE,Env:E2E_OPERATOR_PASSWORD
& "$env:LOCALAPPDATA\AdVergent\tools\exasol.exe" start --deployment advergent
```

Healthy mode: **3 passed, 1 outage-only test skipped**. Actual-outage mode: **3 passed, 1 healthy-only test skipped**. All four distinct browser cases executed across the two modes. Real login -> API -> Exasol displayed INR 4,000 / INR 1,300 / INR 300 with dataset/hash/timestamps and logout succeeded. With the actual Exasol deployment stopped, real login still worked through PostgreSQL, the API reported unavailable, and the UI hid all metric cards. Intercepted-response checks remain separately labelled rendering tests. Screenshots of real healthy and outage states were inspected; clean layout, no stale numbers in outage. Restart and a new authenticated probe succeeded without disabling TLS validation.

Final checks on October 27: `npm.cmd test --prefix frontend -- --grep 'real operator path'` passed after database restoration (1 passed); `npm.cmd ci --prefix frontend` and `npm.cmd run build --prefix frontend` passed from the lockfile. `.\scripts\check-docs.ps1` passed (14 Markdown files, 56 resolving local links, 26 unique acceptance cases); `.\.venv\Scripts\python.exe scripts/check-files.py` passed (45 tracked/untracked source/document files checked directly). `git diff --check` passed. No commit/push performed; initial unrelated image and prior user changes remain preserved.

## Final acceptance and remaining scope

| Phase 1 criterion | Result |
|---|---|
| Authenticated UI -> typed API -> real Exasol golden metric | Passed; SQL returns exact paise totals |
| Operational state and publication in PostgreSQL | Passed with real jobs, sessions and publication pointer |
| Repeat load stable | Passed; same content-derived dataset, two rows, unchanged totals |
| Unauthorized access denied | Passed in real API/browser and persisted-session expiry check |
| Database failure shown | Passed with actual stopped Exasol; no stale metric cards |
| Repeatable setup and exact commands | Delivered, executed on this host; local start/stop/restore verified |

This is foundation verification of A01/A02/A16/A26-related paths, not blanket completion of those catalog cases for the full commerce/action system. A03–A24 business modules and full A25/A26 demo recovery remain later scope. No full finance behavior, merchant ingestion, live adapters, advertising execution or predictive effectiveness is claimed. Production throttling, multi-user auth and hardening are deferred. Hard process-kill recovery of refresh workers, whole-machine reboot recovery and new-machine setup are not tested; the controlled mid-load transaction failure and database restart are tested.

Host capacity limitation: Windows has about 15.8 GiB RAM; free physical memory fell to roughly 1.3 GiB with the local runtime and existing user workloads. The two-line fixture verifies correctness only, not capacity/performance for the proposed 3,000-order dataset. Measure before increasing workload; do not silently reduce acceptance scenarios.

Next: user-requested **separate Phase 2 chat**, read this handoff and current status, then implement commerce fixtures/ingestion/reconciliation and freshness. Reuse the running local stores and existing adapter boundary. Do not discard private config/volumes or unrelated user files. AWS current balance/quota/resource estimate must still be validated before any future provisioning. Schedule: Phase 1 finished early October 27; October 28–30 follow-on targets remain compressed, each original phase still requires its own user-requested chat.
