# Phase 3 handoff

Date: **2026-10-30 (IST)**. Status: **complete for synthetic local ad reporting; Phase 3 exit gate met**. The user explicitly requested this new Phase 3 chat. Phase 4 has not started.

## Changes and deliverables

- [Source models/stateful reporting adapters/importer](../../backend/advergent/ads.py), [deterministic fixture generator](../../backend/advergent/ads_fixture.py), [initial source](../../fixtures/ads-initial-v1.json) and [corrected source](../../fixtures/ads-corrected-v1.json).
- [PostgreSQL migration](../../migrations/003_ad_reporting.sql): separate advertising runs/attempts/publication, independent platform cursors and latest-revision source staging. Existing foundation/commerce pointers and source data are preserved.
- [Exasol adapter](../../backend/advergent/ads_sql.py): immutable normalized account/resource/budget capabilities, typed hierarchy and spend facts, transactional marker, full read-back and real analytical joins/aggregation. Integrated with [existing analytics boundary](../../backend/advergent/exasol.py).
- [Authenticated API](../../backend/advergent/api.py), [typed response models](../../backend/advergent/contracts.py), generated OpenAPI/TypeScript and [ad reporting UI](../../frontend/src/Ads.tsx): totals, campaign/India-day spend, native source hints, budget ownership/shared impact, capabilities/unsupported controls, source freshness and immutable evidence. Foundation cards explicitly identify their separate two-line dataset.
- [Isolated tests](../../backend/tests/test_ads.py), [real-store integration](../../backend/tests/test_ads_integration.py) and [authenticated browser scenarios](../../frontend/tests/ads.spec.ts). Existing rendering substitutes now stub the new ads endpoint explicitly; they are not runtime evidence. Direct [file checker](../../scripts/check-files.py) now covers untracked SQL migrations too.
- Updated product specification, architecture, phase plan, project status, AGENTS and README. Detailed semantics/defaults/commands: [Phase 3 reporting contract](../phase-3-ad-reporting.md).

## Accepted requirements and implemented defaults

Accepted boundaries remain one Indian apparel merchant/warehouse, INR/Asia/Kolkata reporting, real local Exasol, PostgreSQL operational state, synthetic sources, INR 0 infrastructure/API charges and explicit approval for every future advertising mutation. No new deployment, paid service, API credentials or user decision was needed. No live authentication/reporting, advertising mutation, mapping/attribution or later-phase business module is implemented.

Implementation defaults: seed 20261030, two accounts, 16 resources, five budgets, closed half-hour source intervals and 900-second source freshness. Scenario clock is October 30 at 10:00 UTC; initial/corrected source observations are October 29 at 20:00 UTC / October 30 at 10:00 UTC. Historical source observations intentionally show stale. These numerical defaults are not separately user-confirmed preferences.

Meta source uses exact decimal rupee strings; Google uses integer micros divisible by 10,000. Reject foreign currencies, floats and sub-paise inputs rather than silently round. Preserve account timezone/source date, normalize intervals to UTC and derive India day explicitly. The half-hour grain avoids approximating a bucket crossing India midnight; it does not assert external API grain compatibility.

Fixtures cover Meta ad-set-owned and campaign-owned budgets, Search campaigns sharing a separate Google budget, Shopping-like multi-product ad groups and a separately budgeted nonshared PMax-like asset group. A Meta ad-set-budget campaign has no invented campaign budget. Source product-reference hints describe single/multiple scope without establishing commerce mappings. All product-level controls are unsupported/advisory; resource/budget simulated capabilities remain visible with mutations disabled. No recommendation/action system or live capability claim exists.

Each fixture is a complete bounded revision history. Latest revision replaces the whole previous report value, including zero. Duplicate revisions are stable, late older revisions cannot overwrite, delayed new grains add once, and conflicting equal revisions reject. Source cursors and revision state persist in PostgreSQL. Analytical versions are content-addressed by fixture SHA-256 plus `ads-schema-v2:`. Version namespace advanced during development when capability normalization changed; previous development datasets are retained, not rewritten. Independent advertising publication intentionally does not alter commerce/foundation pointers.

## Checks and results — October 30, 2026

All commands ran from the repository root unless noted. Private settings were loaded with `. .\scripts\env.ps1`; the browser password was set using `$env:E2E_OPERATOR_PASSWORD=(Get-Content -Raw .runtime/operator-password.txt).Trim()`. Credentials were never printed or added to documents.

| Exact command/check | Result and important limitation |
|---|---|
| Ordered AGENTS/status/Phase 2 handoff/specification/architecture/phase-plan reads, linked Phase 0 contracts; `git status --short`, `rg --files` | Confirmed only Phase 3 authorized; pre-existing modified/untracked project work and unrelated architecture image preserved |
| `.\.venv\Scripts\python.exe -m advergent.ads_fixture` | Both deterministic input histories generated and strictly validated; final files include native product hints, no commerce mapping |
| `.\.venv\Scripts\python.exe -m advergent.worker migrate` | PostgreSQL third migration and real Exasol ad schema applied using existing private TLS-pinned local runtime |
| `.\.venv\Scripts\python.exe -m advergent.worker ads` | Corrected source loaded and fully read back from Exasol; identical replay stable. `--fixture fixtures/ads-initial-v1.json` selects initial reports; browser tests execute both forms |
| `.\.venv\Scripts\python.exe -m pytest -q` | Final isolated run **34 passed, three real integration tests skipped**. This run alone does not prove the runtime gate |
| `$env:RUN_INTEGRATION='1'; .\.venv\Scripts\python.exe -m pytest -q` | Final real-store run **37 passed, no skips**. Includes existing foundation/commerce regressions and new reporting gate; dependency deprecation/certificate-default warnings remain, with certificate pinning active |
| `.\.venv\Scripts\python.exe scripts/export_openapi.py`; `npm.cmd run types --prefix frontend`; `npm.cmd run build --prefix frontend` | Generated contracts, TypeScript and Vite production build passed |
| `.\.venv\Scripts\python.exe -m uvicorn advergent.api:create_app --factory --host 127.0.0.1 --port 8000` | Existing API restarted with updated code, launched via hidden `Start-Process`; private output logs remain under ignored `.runtime` |
| `npm.cmd test --prefix frontend` with private database/password environment | Final healthy suite **six passed, three outage-only skipped**. Real ad browser test verifies initial/corrected spend, replay, source age/evidence, shared members/impact, unsupported product controls and actual SQL-failure publication preservation |
| `& "$env:LOCALAPPDATA\AdVergent\tools\exasol.exe" stop --deployment advergent`; `$env:E2E_DATABASE_FAILURE='1'; npm.cmd test --prefix frontend` | Final actual outage suite **six passed, three healthy-only skipped**. Foundation, commerce and ads hide unverifiable current values while preserving dataset evidence. No route substitute is used for outage evidence |
| Launcher `start --deployment advergent` in `finally`; healthy browser suite rerun after removing outage flag | Exasol restored using existing state/volumes/certificate pin; authenticated real reports available again |
| `.\.venv\Scripts\python.exe -m advergent.worker refresh`; `.\.venv\Scripts\python.exe -m advergent.worker commerce` | Existing foundation/commerce publications verified/replayed to clear test-induced latest-attempt failures. Same immutable data and original source freshness retained |
| `.\.venv\Scripts\python.exe -m pip check`; `.\.venv\Scripts\python.exe -m compileall -q backend scripts` | Passed |
| `.\scripts\check-docs.ps1`; `.\.venv\Scripts\python.exe scripts/check-files.py`; `git diff --check` | Passed: 18 Markdown files, 110 resolving local links, 26 unique catalog cases, and 69 tracked/untracked source/document/migration files checked directly; no whitespace failures |
| `Get-NetTCPConnection -LocalPort 5432,8563 -State Listen` | Both database listeners remain `127.0.0.1` |

During development, strict source validation caught an incorrect assumption that every campaign has an ancestor-owned budget. Fixed Meta ad-set-owned campaign handling before fixture acceptance. Initial browser run found an ambiguous unsupported-control selector and an existing rendering test that did not stub the new endpoint. Scoped the selector to opened resource details and added explicit rendering-only ads stubs; final suites pass. No database certificate bypass, security-policy change or dependency upgrade was used.

All **nine distinct browser cases** execute across healthy/outage modes; two existing cases use rendering substitutes only. New Phase 3 gate paths use actual authentication, PostgreSQL and Exasol. Screenshots under ignored `.runtime` were visually inspected for layout/readability; they contain only the synthetic demo, not billing evidence.

Final post-restoration probe passed and healthy suite reran successfully (**six passed, three outage-only skipped**). `.runtime/real-ad-capabilities.png` shows the opened shared-budget membership, multi-product PMax capabilities/native hints, normalized source/India dates, zero correction and dataset evidence without overlap. A direct byte comparison of both fixture files against `json.dumps(build_fixture(...), indent=2) + '\n'` also passed; sources reproduce exactly.

## Runtime evidence and gate

| Phase 3 criterion | Verified outcome |
|---|---|
| Spend, INR and reporting timezone reconcile | Initial six grains = 290,021 paise; corrected seven = 210,022. Corrected Meta/Google = 30,010/180,012; India October 29/30 = 59,004/151,018. Google UTC source date remains October 29 across India midnight. Exasol joins/aggregates match independent literal oracles |
| Duplicate imports stable | Duplicate same-grain reports and whole-source replay preserve counts, totals, source observation and completion time; successful replay audited as a separate attempt |
| Delayed/corrected reports replace | Higher revisions replace 10,001 with 9,001 and 80,006 with zero; one delayed interval adds 1,007. Older revisions arriving after corrections cannot overwrite. Conflicting equal revisions and nonadditive parent totals reject |
| Capabilities and unsupported controls visible | Authenticated API/UI expose account/source timezone, hierarchy, exact budget owners/shared members, disabled mutation state and unsupported advisory-only product controls. Shared Search and nonshared PMax budgets are distinct |
| Authenticated real Exasol reporting, freshness/evidence/unavailability | Unauthorized API denied; actual reporting queries include source-age freshness, immutable dataset/hash and query evidence. Actual stopped Exasol suppresses spend, hierarchy and capabilities while retaining publication evidence; healthy queries pass after restoration |
| Replay/failure preservation | Real duplicate-key error after successful inserts rolls back all ad tables/marker and retains prior pointer. Controlled exit after durable pages resumes without refetching committed pages. Failure after real Exasol commit retains prior publication; retry verifies/reuses the orphan and publishes without duplication |

This extends reporting-related A02/A16/A26 evidence and prepares hierarchy/capability inputs for future A11; it does not complete recommendation safety, action authorization or the full A01–A26 catalog.

## Limitations, unverified work and schedule

- No Meta/Google live authentication, SDK/API fidelity, permissions, live-source completeness or sandbox verification. Closed half-hour inputs and exact-paise rejection rules are synthetic application contracts. No claim of live API spend precision/availability.
- No commerce mapping, attribution, mixed-product allocation, platform-reported conversions, full financial recognition or campaign profit. Native source product hints remain unresolved. Separate golden foundation cards must not be joined conceptually to full reporting totals.
- No advertising mutation endpoint/method, approval executor, recommendation, model or later-phase module. Every future mutation, including pause/resume, still requires explicit approval.
- Resume tested with a controlled `SystemExit`, not OS hard kill/reboot/disk-full/recovery after PostgreSQL loss. Commit-before-publication failure tested with an explicit post-commit verification exception, not a hard process crash. No cross-store transaction, cleanup policy, new-machine setup or production security/performance guarantee.
- Reporting response reads the small complete fixture; large-source pagination/capacity benchmarking is unverified. Complete fixture histories are independently importable; no incremental live API completeness protocol exists.
- No infrastructure/API charges, cloud resources, credential rotation, volume deletion, commit or push. AWS remains conditional on current balance/eligibility/full cost preflight.
- Deadline remains October 30, 23:59 IST. Phases 4–14 remain unstarted and the four-pillar demo remains incomplete. No scope/gate was waived; only Phase 3 closes here.

## Next-phase prerequisites and starter prompt

Start Phase 4 only in a **new user-requested chat**. Read AGENTS, current status, this handoff, product specification, architecture, Phase 4 plan and linked attribution/mapping contracts. Reuse all private configuration/certificate pin/volumes and existing publications. Commerce stable IDs and ad hierarchy/native hints are available; no relationship between their IDs has been established. Define explicit mapping provenance/confidence/validity and ambiguity abstention before allocating contribution. The seven-day last-paid-click/no-view-through model is a proposed contract default, not an individually confirmed preference. Preserve platform-reported versus first-party separation and unattributed orders. Build only Phase 4 and verify multi-product/allocation reconciliation with real Exasol and authenticated browser evidence.

Suggested new-chat prompt:

> Start Phase 4 — Mapping/attribution. Implement only Phase 4 in this new chat. Read AGENTS.md, then docs/project-status.md, docs/handoffs/phase-3.md, docs/product-specification.md, docs/architecture.md and Phase 4 in docs/phase-plan.md, followed by linked metric, mapping, attribution, capability and verification contracts. Reuse the verified local PostgreSQL/Exasol foundation, commerce mirror and ad-reporting adapters. Preserve private configuration, certificate pinning, volumes, existing changes and unrelated files. Implement product/ad mappings with provenance, confidence, validity dates, explicit overrides and ambiguity abstention; handle multi-product resources without inventing narrow controls. Implement versioned first-party attribution, keep platform reports separate, retain unattributed orders and ensure each eligible order is assigned at most once with allocations reconciling. Treat native ad product references as unverified hints. Keep Exasol SQL inside the analytics adapter and operational mapping/override state in PostgreSQL. Do not implement live integration, advertising mutations, full finance or later-phase modules. Every future mutation requires explicit approval; infrastructure/API charges remain INR 0. Run isolated, real-store and authenticated browser checks, including ambiguity, multi-product relationships, reconciliation, replay/failure preservation and analytics unavailability. Update product specification, architecture, phase plan, project status, AGENTS.md and docs/handoffs/phase-4.md with exact commands, dates, results and limitations. Mark Phase 4 complete only when its gate passes; do not advance to Phase 5.
