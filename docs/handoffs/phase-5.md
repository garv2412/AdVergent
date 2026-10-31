# Phase 5 handoff

Date: **2026-10-30 (IST)**. Status: **complete for synthetic local finance; Phase 5 exit gate met**. The user explicitly requested Phase 5 only in this separate chat. Phase 6 is unstarted.

## Changes and deliverables

- [Finance source/importer](../../backend/advergent/finance.py), [deterministic generator](../../backend/advergent/finance_fixture.py) and [complete fixture](../../fixtures/finance-v1.json): historical line cost provenance, explicit effective corrections, actual/estimated/missing expenses, cash/receivables, delivery/refund/recovery dates and remaining-unit return reserves.
- [PostgreSQL migration 005](../../migrations/005_finance.sql), [operational publication](../../backend/advergent/operational.py), [worker](../../backend/advergent/worker.py): immutable complete configuration with pinned commerce/ad/attribution, attempts, upstream locks and independent finance publication.
- [Exasol finance adapter](../../backend/advergent/finance_sql.py) integrated into [analytics](../../backend/advergent/exasol.py): transactional typed lines/events/completion marker; source/core verification, SQL economics, unique first-party allocation, connected spend, date views and exact reconciliation. Real failures preserve the prior publication; post-commit retry verifies/reuses orphan datasets.
- [Authenticated API](../../backend/advergent/api.py), [typed contracts](../../backend/advergent/contracts.py), OpenAPI/TypeScript and [finance UI](../../frontend/src/Finance.tsx): separate placed/delivered/cash amounts, nullable realized/expected contribution, ratios/coverage, reserve assumptions/maturity, pinned input observations, transaction/acquisition day views and line provenance. Foundation cards remain separate. Analytics unavailability removes current finance.
- [Isolated cases](../../backend/tests/test_finance.py), [real-store gate](../../backend/tests/test_finance_integration.py), [authenticated finance browser checks](../../frontend/tests/finance.spec.ts). The two existing rendering-substitute tests now stub finance too; they remain rendering evidence only.
- Updated specification, architecture, phase plan, status, AGENTS, metric/verification/attribution contracts and this handoff. Detailed semantics and trusted CLI configuration: [finance contract](../phase-5-finance.md).

## Accepted requirements and implemented defaults

Accepted requirements are exact INR economics, preserved history, unknown missing costs, separated recognition/cash, refunds/COD/RTO/reserve replacement, unique first-party allocations, no platform-claim duplication, real Exasol, PostgreSQL operational ownership, INR 0 charges and no later-phase modules or advertising changes.

Delivery recognition reuses the documented implementation default; it is not an individually merchant-confirmed statutory policy. Fixture delivered timestamps initially equal placement because commerce lacks delivery events; later explicit delivery evidence is supported. Expenses, recovery assessments and settlements are explicit synthetic ledger evidence, not inferred live fees or bank balances. Full-store contribution and POAS remain unknown if any required costs are missing; covered-only subtotals are labelled.

Reserve defaults are 30 days from delivery, 10% future return probability, 80% cost recovery and INR 50 additional return expense per exposed unit. They are uncalibrated assumptions, with calibration sample size zero. Actual returned/refunded units remove their reserve; unreturned units retain exposure, and mature/full outcomes have none. Recovery is independently assessed and can remain unknown. Estimates do not prove effectiveness. Largest-remainder net-merchandise allocation and lexical ties preserve paise; no ledger float arithmetic exists.

The finance as-of is October 30 at 10:00 UTC, covering all input orders and corrected ad grains; source freshness remains pinned to the oldest observation (commerce October 29 at 18:00 UTC). Input cutoffs remain explicit. Snapshot MER uses supplied store net sales and bounded synthetic connected reports; those reports do not prove continuous real merchant-period completeness. Platform claims never affect financial assignment or totals. No incremental-profit claim is made.

## Checks and results — October 30, 2026

All commands ran from the repository root. Private environment: `. .\scripts\env.ps1`. Browser secret: `$env:E2E_OPERATOR_PASSWORD=(Get-Content -Raw .runtime/operator-password.txt).Trim()`. No secret values were printed or documented.

| Exact command/check | Executed result and limitation |
|---|---|
| Ordered AGENTS/status/Phase 4 handoff/specification/architecture/Phase 5 plan and linked metric/financial/attribution/verification contracts; `git status --short`; `rg --files` | Confirmed user authorization for Phase 5 only; preserved existing modified/untracked work and unrelated architecture image |
| `.\.venv\Scripts\python.exe -m advergent.finance_fixture` | Deterministic complete financial source generated; isolated fixture comparison passes |
| `.\.venv\Scripts\python.exe -m advergent.worker migrate`; `.\.venv\Scripts\python.exe -m advergent.worker finance` | Migration 005 and actual Exasol tables applied; default source loaded/verified/published; replay retains source and completion dates |
| `.\.venv\Scripts\python.exe -m pytest -q` | **56 passed, five integration skips**; isolated evidence does not establish real stores |
| `$env:RUN_INTEGRATION='1'; .\.venv\Scripts\python.exe -m pytest -q` after loading private environment | Final **61 passed, no skips** (113.12 seconds); earlier full runs passed 60 before the last isolated edge case was added. Inherited httpx/PyExasol warnings persist without TLS bypass |
| `.\.venv\Scripts\python.exe -m pytest -q backend/tests/test_finance_integration.py` with `RUN_INTEGRATION=1` | **One passed** (66.10 seconds) after added totals/evidence validation; final full suite also includes this case. Final focused rerun after filtering maturity counts to delivered refunds: **one passed** (65.99 seconds) |
| `.\.venv\Scripts\python.exe scripts/export_openapi.py`; `npm.cmd run types --prefix frontend`; `npm.cmd run build --prefix frontend` | Generated contracts and final production TypeScript/Vite build pass |
| Hidden `Start-Process` API using `.\.venv\Scripts\python.exe -m uvicorn advergent.api:create_app --factory --host 127.0.0.1 --port 8000` | Existing app restarted with new API; logs remain under ignored `.runtime` |
| `npm.cmd test --prefix frontend` with real database/operator environment | Final healthy run: **eight passed, five outage-only skips**. Repeated after actual database restart with the same result. First run exposed a missing rendering-only finance stub and a manual worker overlapping the browser import lock; both were corrected before these final sequential runs |
| `npm.cmd test --prefix frontend -- --grep 'real finance A01'` after restarting the API with final code | **One passed** (38.0 seconds); actual authentication, correction/partial reserve, replay and SQL failure preservation; default finance restored in `finally` |
| `& "$env:LOCALAPPDATA\AdVergent\tools\exasol.exe" stop --deployment advergent`; `$env:E2E_DATABASE_FAILURE='1'; npm.cmd test --prefix frontend` | **Eight passed, five healthy-only skips** against actually stopped Exasol. Current financial/cash/ratio/line data removed; publication/input evidence retained |
| Launcher `start --deployment advergent` in `finally`; remove outage flag; `worker probe`, `refresh`, `commerce`, `ads`, `attribution`, `finance`; healthy browser suite rerun | Existing deployment, TLS pin and volumes restored; probe and all five default publications succeed. Post-restart healthy browser suite **eight passed, five outage-only skips** |
| `.\.venv\Scripts\python.exe -m pip check`; `.\.venv\Scripts\python.exe -m compileall -q backend scripts` | Passed |
| `.\scripts\check-docs.ps1`; `.\.venv\Scripts\python.exe scripts/check-files.py`; `git diff --check` | Passed: 22 Markdown files, 172 resolving local links, 26 catalog cases and 91 tracked/untracked source/document/migration files; checks cover new files too |
| `Get-NetTCPConnection -LocalPort 5432,8563 -State Listen` | Both listeners remain `127.0.0.1` |

Early validation caught ad intervals later than commerce observation. Finance now has an explicit compatible as-of and retains the individual source cutoffs instead of assuming identical freshness. One hand-calculated partial-reserve test expectation was corrected to 6,450 paise (79,500 remaining revenue less 20,000 assumed recovery plus 5,000 future fee, times 10%); real SQL agreed. Windows default text decoding introduced mojibake in edited UI strings; repaired to UTF-8 and explicit encodings before final verification. Early development analytical versions remain retained; the final normalization namespace is `finance-v3:`. No private state or prior handoff was removed.

## Gate evidence

| Criterion | Executed evidence |
|---|---|
| A01 exact finance/real query | 3,000 orders, 3,600 lines, 369,912,000 placed paise, 158,757,000 delivered paise less 10,010,000 refunded paise = **148,747,000 net sales paise**. Foundation fixture is excluded. Known `l1-0` contribution is 41,499 paise; its tax-inclusive cash is 84,000 paise. Complete-cost variant reconciles against an independent source-ledger oracle |
| A02 replay | Stable dataset, counts, totals, observation and completion; attempts remain separately audited |
| A03 history | Explicit `l0-0` correction retains null original cost and other lines/prior publications; later-effective correction rejects; no catalog cost lookup rewrites history |
| A04 partial outcomes/reserve | Corrected historical COGS 50,000, explicit recovery 20,000, refund 70,000, variable expense 7,001 yield contribution 51,999 paise. One of two units remains exposed with 6,450 reserve; full/mature outcome removes reserve. Unknown recovery stays unknown |
| A05 COD/RTO | Real `l18-0`: zero recognized sales/sold COGS and **-12,001 paise** contribution; explicit failed losses and prepaid-undelivered/cancellation cases also pass |
| A06 cash distinction | Default net cash **256,575,000 paise** and unsettled delivered COD **44,531,500 paise**, separate from net sales; captured undelivered payments do not create sales |
| A07 unique allocation | Both claims remain separate; `o0` assigns once to Google. All 3,600 lines reconcile once, including 2,996 unattributed orders; spend-only campaigns retained |
| A08 unknown costs | **54 incomplete lines, 98.50% line coverage**; full contribution/POAS null, covered subtotal **76,063,310 paise**. Missing recovery/expense tests preserve nulls; fully covered variant yields actual complete totals |
| Ratios/events | Actual zero-connected-spend source gives null POAS/MER, before=after contribution; negative remains negative. Transaction/acquisition sales/cash reconcile with event dates and original acquisition |
| Failure/pinning | Real SQL duplicate-key rollback empties lines/events/marker; pointer preserved. Post-commit verification failure retains prior publication and retry reuses orphan. Changed ad input labels retained finance and blocks new finance until attribution republished. Typed corruption returns unavailable and is restored |
| Actual outage/browser | Real operator authentication, financial evidence/correction/partial-reserve/replay/failure preservation pass. Actual stopped Exasol removes all current finance; restart and healthy replays/browser suite pass. All 13 distinct browser cases execute across modes; two inherited cases are rendering substitutes only |

Healthy and actual-outage finance screenshots under ignored `.runtime` were inspected for readable cards, financial allocations, historical provenance, source/input/assumption evidence and absence of current results during outage. No screenshot or private log was added to repository documents. Final review additionally verifies tax-inclusive payment refunds on undelivered orders: cash changes, recognized revenue and sold-COGS recovery do not. This edge case is isolated evidence; the full finance real-store/browser fixture exercises delivered refunds and COD/RTO separately.

## Limitations and next phase

Synthetic evidence does not prove live API fidelity, source completeness, calibrated reserves, incremental profit, statutory accounting or a bank/settlement reconciliation system. The full API includes the bounded 3,600-line snapshot; UI pages provenance, but large-source API pagination/performance is unverified. Configuration uses complete immutable trusted CLI sources, with no browser editing or later approval module. Retained operational sources and analytical versions have no cleanup policy. Hard-kill/reboot/new-machine/disk-full recovery, production hardening and capacity beyond this fixture remain unverified.

All default publications were restored after destructive failure/outage checks; the application remains available at `http://127.0.0.1:8000`. Historical input age remains stale after replay. No provisioning, billing upgrade, paid API/dependency, live integration, inventory/recommendation module, advertising mutation, commit or push. Private environment/certificates/launcher state/volumes and unrelated files remain preserved. Deadline remains October 30 at 23:59 IST; earlier targets were missed, and the full four-pillar milestone is incomplete. Only Phase 5 may close here.

Start Phase 6 only in a new user-requested chat. Read AGENTS, status, this handoff, specification, architecture, Phase 6 gate and linked inventory/financial/verification contracts. Reuse the same private local stores, freshness/unknown-cost evidence and pinned finance/attribution interfaces. Keep mixed-product capability limits and every advertising mutation's explicit-approval boundary. Do not begin Phase 6 in this chat.
