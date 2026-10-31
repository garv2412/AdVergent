# Phase 1 foundation setup

Local operation is accepted by the user on October 27, 2026. No AWS provisioning is required for this route. This guide does not establish that database/runtime gates have passed; consult the [Phase 1 handoff](handoffs/phase-1.md).

## Runtime and installation

Use Python 3.14 and Node 24 on this Windows host. PowerShell commands below run from the repository root. Keep credentials in ignored `.env`, never in command output or documentation.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
npm.cmd ci --prefix frontend
```

If Windows blocks SQLAlchemy's optional compiled extension, build its supported pure-Python distribution instead of changing Windows security policy:

```powershell
$env:DISABLE_SQLALCHEMY_CEXT='1'
.\.venv\Scripts\python.exe -m pip install --force-reinstall --no-binary sqlalchemy --no-deps sqlalchemy==2.1.6
```

Rollup uses the official WebAssembly package through an npm alias/override, recorded in the lockfile. Do not replace it with the native Windows module on this host.

## Local databases and private configuration

Install Podman 5.8.3 using `winget install --id RedHat.Podman --exact --version 5.8.3`. Initialize and start a default WSL machine if none exists. Check available host RAM first; do not overwrite another machine's configuration.

```powershell
podman machine list
podman machine init --cpus 2 --memory 4096 --disk-size 30
podman machine start
.\.venv\Scripts\python.exe scripts/configure.py
. .\scripts\env.ps1
.\scripts\start-postgres.ps1
```

For unattended local setup, `scripts/configure.py --generate` saves the operator password to ignored `.runtime/operator-password.txt` without printing it. Protect `.env` and `.runtime` as private files. On this host these have been generated; do not overwrite them.

The PostgreSQL start script passes the password through the environment and binds only to loopback. An alternative for an already working Docker installation is `docker compose up -d postgres`. Both use PostgreSQL 17.9 Alpine and a durable named volume. These are alternatives, not simultaneous deployments. Do not run `compose down -v` unless deletion of operational data is intended.

Use the official signed Exasol Personal Windows x86-64 launcher pinned to 2.3.0 from [its release](https://github.com/exasol/exasol-personal/releases/tag/v2.3.0). The Windows ZIP SHA-256 published on the release asset page is `6300c83528d2f6a7a79a468351564bc75e88004f07b5cf28429be80ff94e6fcf`. Verify it before extracting/running. This host stores tools outside Git under `%LOCALAPPDATA%\AdVergent\tools`.

```powershell
& "$env:LOCALAPPDATA\AdVergent\tools\exasol.exe" install local --deployment advergent --ports db:8563
```

Keep deployment state, connection information and logs outside Git. Do not paste `exasol info` output into the handoff: it can contain credentials. Restrict the local database to the local application; verify listener/firewall behavior before any network access. Confirm the TLS certificate fingerprint via trusted local deployment information. Set `.env` to `EXASOL_DSN=127.0.0.1/FINGERPRINT:8563` for a self-signed local certificate, or configure a trusted CA. `nocertcheck` is rejected by the adapter. Change initial database credentials before exposing any service, and use a dedicated AdVergent schema user with CREATE SCHEMA/TABLE, SELECT and INSERT privileges for setup and loading. Runtime SELECT-only credentials can be separated in a later hardening change.

The local launcher currently omits a certificate fingerprint and recommends skipping verification. Keep verification enabled: copy the public certificate directly from the trusted local container (`podman cp CONTAINER_NAME:/exa/certificates/fullchain.pem .runtime/exasol-fullchain.pem`), then run:

```powershell
.\.venv\Scripts\python.exe scripts/bootstrap-exasol.py "$env:USERPROFILE\.exasol\personal\deployments\advergent\deployment.json" --certificate .runtime/exasol-fullchain.pem
```

Use the container name shown by `podman ps`. This script derives the fingerprint from that trusted certificate, reads the initial admin credential privately from launcher `secrets.json`, creates the dedicated application user, rotates the admin password, and updates ignored `.env` and launcher secrets consistently. It refuses to overwrite independently configured application credentials. Recovery credentials remain in ignored `.runtime/exasol-bootstrap.json`; preserve them privately. Repeated bootstrap after partial admin rotation requires the private rotated password in `EXASOL_BOOTSTRAP_PASSWORD` (never paste it in chat or logs). Without `--certificate`, bootstrap requires a fingerprint in trusted launcher state; it never accepts an unverified network certificate.

## Build, initialize, query

```powershell
. .\scripts\env.ps1
.\.venv\Scripts\python.exe scripts/export_openapi.py
npm.cmd run types --prefix frontend
npm.cmd run build --prefix frontend
.\.venv\Scripts\python.exe -m advergent.worker migrate
.\.venv\Scripts\python.exe -m advergent.worker probe
.\.venv\Scripts\python.exe -m advergent.worker refresh
.\.venv\Scripts\python.exe -m uvicorn advergent.api:create_app --factory --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` and sign in with the configured operator password. The cookie is HttpOnly, SameSite Strict, expires after one hour and is stored as a hash in PostgreSQL. POST requests require an exact Origin and application header. For HTTPS deployment set `COOKIE_SECURE=true` and the exact `APP_ORIGIN`; the local HTTP setting is only for loopback. There is no production login throttling or multi-user account management yet.

The golden fixture expects sales INR 4,000, product costs INR 2,200, variable costs INR 500 and ad spend INR 1,000, yielding INR 1,300 before ads and INR 300 after ads. All amounts are integer paise. It is a two-line delivered-sales foundation fixture, not verification of full financial behavior or A01–A08.

`refresh` loads immutable content-addressed datasets in Exasol, checks the golden metric, then publishes in PostgreSQL. A global PostgreSQL advisory lock serializes refresh workers. Failed jobs preserve the prior publication; a subsequent worker marks interrupted running jobs failed. There is no cross-database atomic transaction. Replaying identical fixture bytes reuses the dataset ID and does not append analytical rows. Evidence includes dataset ID, fixture hash, publication time and real query time. No UI action can mutate advertising.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q
$env:RUN_INTEGRATION='1'
.\.venv\Scripts\python.exe -m pytest -q -m integration
Remove-Item Env:RUN_INTEGRATION
npm.cmd test --prefix frontend
.\scripts\check-docs.ps1
.\.venv\Scripts\python.exe scripts/check-files.py
git diff --check
```

Real integration tests require dedicated PostgreSQL and Exasol instances configured via environment; they create schemas and refresh records. They are opt-in and skipped by default. Supply the operator password privately as `E2E_OPERATOR_PASSWORD` for the real authenticated browser path. The browser contract fixture test uses intercepted responses and is only UI verification. Browser tests use installed Chrome by default; set `PLAYWRIGHT_CHANNEL=msedge` for installed Edge or install Playwright Chromium and set `PLAYWRIGHT_CHANNEL=chromium` on hosts permitting that binary. Downloaded Chromium is blocked on this host; no security policy was changed.

For a login/auth-denial UI smoke check without databases, run `.\.venv\Scripts\python.exe scripts/serve-preview.py`. It deliberately configures unreachable database endpoints and a random unknown password; it cannot demonstrate the golden metric. Do not confuse this preview with the operational slice.

Stop the API with Ctrl+C. Stop PostgreSQL using `podman stop advergent-postgres` (or `docker compose stop postgres`). Stop Exasol using the launcher with `stop --deployment advergent`. Stopping Exasol leaves the shared Podman machine running; stop that only after checking other workloads. Preserve volumes/deployment state for restart.
