# Phase 4 handoff

Date: **2026-10-30 (IST)**. Status: **complete for synthetic local mapping/attribution; Phase 4 exit gate met**. The user explicitly requested this Phase 4 chat. Phase 5 has not started and requires a separate user-requested chat.

## Changes and deliverables

- [Mapping/attribution contracts and importer](../../backend/advergent/attribution.py): exact scoped product sets, confidence/provenance, half-open validity, explicit overrides and ambiguity abstention. Versioned first-party last-paid-click assignment, event deduplication, ties/unattributed reasons, separate synthetic platform claims.
- [Deterministic generator](../../backend/advergent/attribution_fixture.py) and [immutable source](../../fixtures/attribution-v1.json): reviewed single/multiple sets, conflicting candidates, low confidence, explicit override, duplicate/expired/post-order/view/unidentifiable/tied clicks, mixed purchased products and overlapping Meta/Google claims.
- [PostgreSQL migration 004](../../migrations/004_attribution.sql): immutable configuration/override snapshots, pinned commerce/ad versions, attempts and independent publication. Existing foundation/commerce/ads publications remain separate.
- [Exasol adapter](../../backend/advergent/attribution_sql.py): transactional full evidence, typed unique order assignments, completion marker, full read-back and real order-line/variant/refund joins with exact count/paise reconciliation. Integrated with [analytics adapter](../../backend/advergent/exasol.py), [worker](../../backend/advergent/worker.py) and [operational store](../../backend/advergent/operational.py).
- [Authenticated API](../../backend/advergent/api.py), [typed contracts](../../backend/advergent/contracts.py), generated OpenAPI/TypeScript and [inspection UI](../../frontend/src/Attribution.tsx). Visible model/input IDs/hash/source age/mapping evaluation date, provenance/validity, first-party and separate platform views, changed-input warning, failed publication and analytics unavailability.
- [Isolated tests](../../backend/tests/test_attribution.py), [real-store gate](../../backend/tests/test_attribution_integration.py) and [authenticated browser checks](../../frontend/tests/attribution.spec.ts). Existing rendering substitutes explicitly stub attribution; these two cases remain rendering evidence only.
- Updated product specification, architecture, phase plan, project status, AGENTS and README. Full semantics, implementation defaults and configuration commands: [Phase 4 contract](../phase-4-mapping-attribution.md).

## Accepted requirements and implemented defaults

Accepted boundaries remain one Indian merchant/warehouse, INR, real Exasol analytics, PostgreSQL operational state, synthetic inputs, INR 0 infrastructure/API charges and explicit approval for every future advertising mutation. The user authorized only Phase 4. No provisioning, paid dependency/API, advertising write, live integration or later module was needed.

The documented proposed seven-day last-identifiable-paid-click/no-view-through model is implemented as visible version `last-paid-click-7d-no-view-v1`. It is an implementation default, not an individually confirmed merchant preference. Seven days includes both boundaries; latest-time ties across campaigns abstain. Event IDs deduplicate; source order, names, platform claims and product hints cannot establish assignment. All placed orders retain one campaign or unattributed row.

Mapping candidate confidence floor is 9,000 basis points. Exact-resource reviewed sets, half-open validity and explicit override precedence are defaults; conflicting product sets at the winning precedence abstain. Full provenance/actor/reason/confidence/validity is retained even for superseded/low-confidence evidence. Multi-product sets do not imply narrow controls, product spending fractions or parent/child inheritance. Mapping evaluation time is the evidence fixture's observation; freshness uses the oldest input observation. Source replay never makes historical evidence fresh.

Configuration/override changes use a complete new immutable JSON source via `worker attribution --fixture PATH`, with PostgreSQL retaining the full snapshot. No browser mapping editor, user approval module or live tracking exists. These are trusted local operational configuration changes, without any advertising mutation.

Placed merchandise allocation is deliberately distinct from financial recognition: all 3,000 placed orders, including undelivered/cancelled/RTO, participate. Actual purchased lines allocate to the single assigned campaign or unattributed bucket. Product allocations use commerce variants, not advertised product sets. Refund links preserve original assignment and actual refund timestamp, without calculating refund economics. Full contribution/finance belongs to Phase 5.

## Checks and results — October 30, 2026

Commands ran from the repository root. Private environment was loaded with `. .\scripts\env.ps1`; browser password was loaded with `$env:E2E_OPERATOR_PASSWORD=(Get-Content -Raw .runtime/operator-password.txt).Trim()`. No private values were printed or copied into documents.

| Exact command/check | Result and limitations |
|---|---|
| Ordered AGENTS/status/Phase 3 handoff/specification/architecture/phase-plan and linked Phase 0/reporting contracts; `git status --short`, `rg --files` | Confirmed only Phase 4 authorized; existing modified/untracked work and unrelated architecture image preserved |
| `.\.venv\Scripts\python.exe -m advergent.attribution_fixture` | Deterministic complete source generated; isolated byte-comparison test confirms reproducibility |
| `.\.venv\Scripts\python.exe -m advergent.worker migrate` | Fourth PostgreSQL migration and actual Exasol schema applied with existing pinned connection, credentials/state/volumes preserved |
| `.\.venv\Scripts\python.exe -m advergent.worker attribution` | Default source loaded, fully read back/reconciled and published; repeated replay stable |
| `.\.venv\Scripts\python.exe -m pytest -q` | **46 passed, four integration tests skipped**; isolated evidence alone does not prove real runtime |
| `$env:RUN_INTEGRATION='1'; .\.venv\Scripts\python.exe -m pytest -q` after loading private environment | **50 passed, no skips**; includes foundation/commerce/ad regressions and new Phase 4 gate. Existing httpx deprecation and PyExasol certificate-default warnings remain; fingerprint pinning remains active |
| `.\.venv\Scripts\python.exe scripts/export_openapi.py`; `npm.cmd run types --prefix frontend`; `npm.cmd run build --prefix frontend` | Generated typed contracts and production TypeScript/Vite build passed |
| `.\.venv\Scripts\python.exe -m uvicorn advergent.api:create_app --factory --host 127.0.0.1 --port 8000` via hidden `Start-Process` | Existing API restarted with final code; private logs under ignored `.runtime` |
| `npm.cmd test --prefix frontend` with real private database/password environment | **Seven passed, four outage-only skipped**. Real authentication/Exasol mappings, override/ambiguity/multi-product display, exact allocation, separate claims, replay and genuine SQL failure preservation pass |
| `& "$env:LOCALAPPDATA\AdVergent\tools\exasol.exe" stop --deployment advergent`; `$env:E2E_DATABASE_FAILURE='1'; npm.cmd test --prefix frontend` | **Seven passed, four healthy-only skipped** against actually stopped Exasol. Current mapping/allocation/claim data disappears; publication/model/input evidence remains. No outage route substitute |
| Launcher `start --deployment advergent` in `finally`, remove outage flag; `worker probe`, `refresh`, `commerce`, `ads`, `attribution`; healthy browser suite rerun | Database restored with existing TLS pin/state/volumes; probe and all default publications/replays pass. Final healthy browser run **seven passed, four outage-only skipped** |
| `.\.venv\Scripts\python.exe -m pip check`; `.\.venv\Scripts\python.exe -m compileall -q backend scripts` | Passed |
| `.\scripts\check-docs.ps1`; `.\.venv\Scripts\python.exe scripts/check-files.py`; `git diff --check` | Passed: 20 Markdown files, 138 resolving local links, 26 unique catalog cases and 80 tracked/untracked source/document/migration files checked directly |
| `Get-NetTCPConnection -LocalPort 5432,8563 -State Listen` | Both database listeners remain `127.0.0.1` |

The first real-store run caught strict response timestamp parsing when source models were reused in the API. Changed the typed analytical response boundary to parse its JSON representation, retaining strict source validation. Final real-store and browser checks pass. Initial development dataset versions remain retained; default source was regenerated after adding the cross-product purchase scenario. The final direct file checker caught two Windows-encoded inserted dashes in edited documents; converted only the invalid bytes to UTF-8 and reran both document/file checks successfully. No TLS bypass, dependency upgrade or security-policy change was used.

All **eleven distinct browser cases** execute across the two modes. Two pre-existing cases use rendering substitutes only; new Phase 4 paths use actual operator authentication, PostgreSQL and Exasol. Synthetic screenshots under ignored `.runtime` were inspected for layout/readability, including mapping provenance, purchased-product allocation and actual-outage evidence.

## Gate evidence

| Phase 4 criterion | Verified result |
|---|---|
| Provenance/confidence/validity/overrides | All evidence retained and exposed; exact validity start resolves, exclusive end/earlier instant abstain; explicit override selects full set; conflicting override sets abstain; unknown identity/product and malformed evidence reject |
| Ambiguity and hints | Shopping-like resource with competing product sets abstains; low-confidence resource remains unmapped; native hints and hierarchy names/parents never create relationships |
| Multi-product correctness | PMax-like resource maps to `p0,p1` without a narrow control. Purchased products `p0,p1,p5,p6` allocate to its campaign from actual order lines, without constraining purchases to the advertised set or duplicating order totals |
| Versioned first-party/separate platforms | Latest eligible identifiable paid click wins once; exact seven-day boundary included; expired/view/post-order/unidentifiable events excluded; identical duplicate stable, conflicting duplicate rejects; latest-time cross-campaign tie remains unattributed. Both platforms claim `o0`, but first-party assigns it once to Google |
| Exact allocation and retained unattributed | Real Exasol: **3,000 orders, 3,600 lines, 369,912,000 paise** placed merchandise, **143 refund links**. Google PMax: three orders/six lines/651,000 paise; Meta ABO: one order/one line/80,000 paise; unattributed: **2,996 orders/3,593 lines/369,181,000 paise**. Product allocation and refund-link counts reconcile; no full-finance claim |
| Replay, locks and pinned inputs | Same source/input IDs retain dataset, completion and observation; actual held upstream advisory lock blocks import. Publishing different ad input leaves previous attribution pinned and visibly marks dependency mismatch; original ad publication restored |
| Failure preservation | Genuine SQL duplicate-key error rolls back all three analytical tables/marker and retains prior pointer; retry succeeds. Failure after actual analytical commit retains prior pointer; retry verifies/reuses orphan. Deliberate typed/core mismatch yields unavailable rather than current data, then restored |
| Authentication/unavailability | Unauthorized endpoint denied; real authenticated API/UI expose model/source/input/query evidence. Actually stopped Exasol hides mapping/allocation/claim data and retains publication evidence; final healthy replay/browser checks pass after restart |

This prepares A07/A11/A16/A26. It does not complete A07 contribution recognition, the full financial catalog, recommendation safety or advertising execution.

## Limitations, unverified work and schedule

- Synthetic explicit click/order linkage and platform claims do not prove live integration, consent/identity tracking, source completeness, API fidelity or incremental/model effectiveness. Platform hierarchy is the pinned synthetic snapshot, not a historical live service.
- Configuration is immutable complete-source import through the local trusted worker; no browser edit workflow, per-user authorization or approval module. Threshold/window changes require a new supported model/schema version and tests. No automatic candidate discovery, fuzzy matching or spend allocation to product sets.
- Placed merchandise precedes tax/refunds/delivery recognition. No costs, contribution, revenue recognition, reserves, finance ratios, LTV/cohort module, recommendation, executor or advertising mutation. Every future advertising change still requires explicit approval.
- Retry and commit-before-publication recovery tested with injected exceptions; OS hard kill/reboot/new-machine/disk-full/PostgreSQL-loss recovery, cleanup, large-source pagination/capacity, production security and high availability remain unverified. Configuration/source staging and old Exasol versions have no cleanup policy.
- No cloud resources, paid API, billing upgrade, credential rotation, certificate bypass, volume deletion, commit or push. Existing private configuration, certificate pin and volumes preserved. INR 0 charges remain a hard boundary; future AWS provisioning requires current preflight.
- Deadline remains October 30 at 23:59 IST. The earlier schedule targets were missed and the full four-pillar milestone is incomplete. Only Phase 4 closes here; Phases 5–14 remain unstarted.

## Next-phase prerequisites and starter prompt

Start Phase 5 only in a **new user-requested chat**. Read AGENTS, current status, this handoff, product specification, architecture, Phase 5 plan and linked financial/metric/verification contracts. Reuse pinned inputs and unique order assignments; all actual line economics must reconcile through Exasol without mixing platform claims or the separate foundation cards. Respect delivery/COD/RTO/refund/cost-coverage rules and distinguish proposed defaults from user-approved requirements. Preserve private environment/TLS/volumes and INR 0 boundaries. No Phase 5 implementation began in this chat.
