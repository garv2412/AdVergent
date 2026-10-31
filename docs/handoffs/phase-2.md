# Phase 2 handoff

Date: 2026-10-30 (IST). Status: **complete for the synthetic local commerce mirror; Phase 2 exit gate met**. The user explicitly requested this new Phase 2 chat. This chat does not start Phase 3.

## Changes and deliverables

- [Commerce source models/importer](../../backend/advergent/commerce.py), [deterministic fixture generator](../../backend/advergent/commerce_fixture.py) and [source fixture](../../fixtures/commerce-v1.json).
- [PostgreSQL migration](../../migrations/002_commerce.sql), operational run/checkpoint/receipt/staging/attempt state, and a separate commerce publication pointer. Foundation publication and golden metric are preserved.
- [Exasol commerce adapter](../../backend/advergent/commerce_sql.py): seven typed core tables, retained source payloads, transactional batched loading, completion marker, complete read-back and analytical queries. Vendor SQL stays behind the adapter.
- [Authenticated API](../../backend/advergent/api.py), [response contracts](../../backend/advergent/contracts.py), generated OpenAPI/TypeScript types and [commerce UI](../../frontend/src/Commerce.tsx): real totals, dataset-pinned record pagination, freshness, failed-import/unavailable states and evidence.
- [Source validation tests](../../backend/tests/test_commerce.py), [real-store integration](../../backend/tests/test_commerce_integration.py), [browser tests](../../frontend/tests/commerce.spec.ts) and extended foundation freshness/API tests.
- Updated product specification, architecture, phase plan, project status, README and AGENTS. Detailed semantics and commands: [commerce contract](../phase-2-commerce.md).

## Decisions and defaults

Accepted requirements remain single Indian apparel merchant, one warehouse, domestic INR, synthetic source data, real Exasol analytics, approval for every future advertising mutation and INR 0 infrastructure/API charges. Local whole-application fallback was already accepted in Phase 1. No new cloud deployment or external service was needed.

Implemented defaults: seed 20261030; 180-day source history; 30 products, 180 variants, 1,000 customers and 3,000 orders. The source has 3,600 lines, 143 refunds and 180 warehouse records. Fixed observation/scenario time is October 29 at 18:00 UTC. Source freshness uses a 900-second implementation constant based on the earlier proposed inventory default. These numerical defaults are not described as individually user-approved rules.

PostgreSQL temporary source staging is operational recovery input, not the analytics mirror or dashboard fallback. Complete authoritative fixture reconciliation repairs missing creates/updates and sweeps missed deletes; a future live adapter must establish snapshot completeness independently. Historical costs and missing-cost provenance are preserved. Refunds do not imply restocking. Available stock already excludes commitments; only the separately modelled merchant reserve is subtracted for sellable units.

Import runs are content-addressed by source hash and schema version. Attempts have separate audit rows, including replay verification. A replay preserves the dataset completion timestamp and does not refresh the source observation. An explicit prior fixture can select an older version; that is not new evidence. Completed analytical data is immutable through the importer. No automatic staging/version cleanup is implemented.

## Checks and results (October 30, approximately 17:00–17:25 IST)

Commands run from repository root. Private configuration loaded with `. .\scripts\env.ps1`; passwords were never printed or placed in tracked files.

| Command/check | Result and limitation |
|---|---|
| Required ordered document reads, `git status --short`, `rg --files` | Phase 1 verified foundation reused; existing modified/untracked project work and unrelated architecture image preserved |
| `Get-CimInstance Win32_OperatingSystem` | About 4.8 GiB free before starting stores; about 3.3 GiB observed with local runtime/browser work. Snapshot only, not peak-memory or performance certification |
| Existing Podman `machine start`, PostgreSQL container `start`, pinned launcher `start --deployment advergent` | Existing state/volumes reused. No reinstall, credential reset, cloud resource or paid API |
| `.\.venv\Scripts\python.exe -m advergent.commerce_fixture` | Deterministically generated 4,889,375-byte source; source validation and relationships pass |
| `.\.venv\Scripts\python.exe -m advergent.worker migrate` | Both stores migrated. Initial attempt raced database startup; retry exposed reserved word `RECOVERY` in Exasol DDL. Fixed quoted typed columns in adapter and reran successfully; no TLS bypass |
| `.\.venv\Scripts\python.exe -m advergent.worker commerce` | Full dataset loaded, every payload/core column read back, published. Replay reused dataset, retained counts and audited a successful verification attempt |
| `$env:RUN_INTEGRATION='1'; .\.venv\Scripts\python.exe -m pytest -q` | **19 passed, no skips**, final suite after attempt-audit and conflict tests. Uses actual PostgreSQL/Exasol for both integration tests. Existing dependency deprecation/certificate-default warnings remain; pinned TLS is active |
| `.\.venv\Scripts\python.exe scripts/export_openapi.py`; `npm.cmd run types --prefix frontend`; `npm.cmd run build --prefix frontend` | Passed generated contracts, TypeScript and Vite production build |
| `npm.cmd test --prefix frontend` with private `E2E_OPERATOR_PASSWORD` | Healthy: **5 passed, 2 outage-only skipped**. Initial test failure was an ambiguous heading selector after adding commerce evidence; tightened selector and reran successfully |
| Launcher `stop --deployment advergent`; browser suite with `E2E_DATABASE_FAILURE='1'` | Actual outage: **5 passed, 2 healthy-only skipped**. Login still uses PostgreSQL; foundation numbers and commerce records/totals disappear while publication/source evidence remains. This is not an intercepted outage |
| Launcher `start --deployment advergent`; final healthy browser checks | Exasol restored with existing certificate pin; healthy authenticated queries pass again |
| `Get-NetTCPConnection -LocalPort 5432,8563 -State Listen` | Both listeners `127.0.0.1` |
| `.\.venv\Scripts\python.exe -m pip check`; `.\.venv\Scripts\python.exe -m compileall -q backend scripts` | Passed |
| `.\scripts\check-docs.ps1`; `.\.venv\Scripts\python.exe scripts/check-files.py`; `git diff --check` | Passed: 16 Markdown files, 80 resolving local links, 26 unique catalog cases; 55 tracked/untracked source/document files checked directly, including new fixture/documents |

Real integration evidence: committed source pages survive a controlled `SystemExit`; the retry invokes no committed-page callback. Duplicate receipt is singular; late stock revision cannot replace newer zero stock; a tombstone cannot be resurrected by a late create. A missed product, stock record, refund and deletion produce four reconciliation repairs. Full analytical read-back matches source, placed-value/sellable/refund totals reconcile independently. An injected duplicate at the end of the real SQL load fails after successful inserts and rolls back all seven tables and the completion marker; prior publication remains, and retry succeeds from the completed source checkpoint. Equal source revisions with conflicting content roll back the whole page, cursor and receipts. API checks cover auth denial, stale source age, pagination bounds and changed-publication rejection. Isolated tests additionally cover fresh/unknown freshness, null missing costs, unsupported currency, floats, future/naive timestamps and invalid source relationships.

All **7 distinct browser cases** executed across healthy/outage modes. Two use labelled route substitutes for rendering only; the other five use actual API/database paths. Real commerce browser checks show 3,000 orders, record pagination, intentionally stale source time and escaped malicious catalog text. Desktop screenshots were visually inspected: layout and source fields are readable, without overlap. Screenshots remain ignored under `.runtime`; no sensitive billing material is recorded.

## Exit gate

| Phase 2 criterion | Result |
|---|---|
| Fixture-based catalog, orders, refunds and inventory mirror | Passed, plus synthetic customers/order lines; full 3,000-order source loaded into real Exasol |
| Duplicates and out-of-order changes reconcile | Passed in operational staging, source revision/tombstone checks and analytical replay |
| Missed changes reconcile | Passed complete snapshot repair/sweep; four deliberate repairs |
| Import resumes | Passed controlled process exit after page commit and retry after actual SQL rollback; cursor does not replay completed pages |
| Freshness visible | Passed real authenticated UI; source-age stale state survives replay and outage hides current values |

This extends A02/A16/A26-related commerce evidence and A24 safe text rendering; it is not blanket completion of A01–A26, full finance, recommendation safety or an action authorization system.

## Limitations, unresolved work and schedule

- No live Shopify authentication/webhook/API fidelity, live history coverage, ads, attribution, full contribution/refund/COD financial recognition, inventory recommendations, models or advertising execution.
- Foundation contribution cards intentionally remain the separate hand-calculated two-line dataset. They must not be represented as finance for the commerce mirror.
- Resume uses a controlled process exit, not an OS hard kill, host reboot, disk-full condition or PostgreSQL-loss recovery. Crash between Exasol commit and PostgreSQL publication is designed to verify/reuse the marker but was not separately fault-injected. There is no cross-database transaction.
- The 3,000-order source loaded on this host; no scale/load benchmark, measured peak memory, new-machine setup or production-hardening claim. Source staging, receipts and old analytical versions are retained without cleanup.
- No paid upgrade, cloud resource, external mutation, commit or push. AWS still requires current balance/eligibility/full cost preflight before provisioning.
- Deadline remains October 30, 23:59 IST. Prior October 28–29 targets were missed; Phases 3–14 are unstarted. The complete four-pillar demo is not delivered by this phase, and no scope/gate was waived.

## Next-phase prerequisites

Start **Phase 3 only in a new user-requested chat**. Read this handoff, current status, product/architecture and Phase 3 plan. Reuse private `.env`, `.runtime`, certificate pin, launcher state and volumes. Implement stateful Meta/Google fixture reporting adapters, hierarchy/spend normalization, delayed-report replacement and visible capabilities. Read the currency/timezone/capability contracts before changes. Commerce IDs and immutable dataset evidence are ready for later mapping/attribution; financial/action behavior remains later-phase work. Every advertising mutation still requires explicit approval.
