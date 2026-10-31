# AdVergent — Hackathon submission draft

Prepared October 31, 2026 IST. Track confirmed by the submitter. Replace the video placeholder before submitting; this draft does not establish completion of the pending Phase 14 gate.

## Selected problem track

**Track 02 — Customers, Channels & Demand**

## Problem statement

Apparel merchants make advertising decisions across disconnected sales, customer, inventory and channel reports. Advertising dashboards can show attractive revenue while returns, cash-on-delivery failures, missing costs or unavailable sizes make the same campaign commercially unsafe. Platform attribution can overlap, and a promising demand signal does not necessarily mean a product is ready for more spending.

Merchants need one evidence-based view of which customers, channels and products contribute value, where demand is emerging, and when inventory or insufficient evidence should block a recommendation.

## Solution and track fit

AdVergent is a working local decision-support prototype for a single Indian apparel merchant, using real Exasol Personal analytics with reproducible synthetic commerce and advertising data.

- **Customers:** first-party attribution and first-delivered-purchase cohorts, with separate mature and immature 60/90-day contribution windows.
- **Channels:** normalized Meta-shaped and Google-shaped reports, exact INR spend reconciliation, reviewed product mappings and contribution after advertising.
- **Demand:** deduplicated product-view, cart and click signals, inventory cover and size availability, conservative breakout ranking and constrained budget scenarios.

A unified decisions view resolves conflicting recommendations, prioritizes inventory protection and explains abstentions. Missing costs remain unknown; stale evidence does not become fresh simply because it is reloaded. Advertising changes are simulated and require separately persisted explicit approval. The prototype does not connect to live advertising accounts or Shopify.

## Working solution using Exasol Personal

Exasol Personal is the analytical engine, accessed through encrypted, certificate-verified PyExasol connections. Actual SQL loads and joins commerce, advertising, attribution, financial, inventory and diagnostic evidence, then reconciles analytical results. PostgreSQL stores operational jobs, publication pointers, sessions, approvals and audit history. FastAPI exposes authenticated endpoints to a React/TypeScript interface.

The synthetic commerce dataset includes 30 products, 180 variants, 1,000 customers and 3,000 orders. A separate foundation example verifies INR 4,000 sales minus INR 2,200 product costs, INR 500 variable costs and INR 1,000 advertising spend equals INR 300 contribution after ads. This foundation example is separate from full-commerce results.

Documented Phase 13 verification includes 269 passing broad non-mutating real-store tests, followed by one separate focused real-store pass. Healthy and actual-Exasol-outage browser runs each passed 15 cases with 12 mode-specific skips. Phase 14 hardening remains in progress; these results are prior recorded evidence, not checks rerun for this submission draft. No measured merchant uplift, calibrated predictive accuracy or production-readiness claim is made.

## Public code repository

Repository: https://github.com/garv2412/AdVergent

Licence: MIT; copyright 2026 Garv Gupta. See [LICENSE](../LICENSE).

The implementation, synthetic fixtures, locked dependency manifests and reproduction documents are included in this repository. Private credentials, runtime files and local database state are excluded.

## Setup and reproduction

The documented reference environment is Windows/PowerShell, Python 3.14, Node.js 24, PostgreSQL 17.9 and Exasol Personal launcher 2.3.0 with Podman. Fresh-machine reproduction has not been verified.

1. Clone the complete published repository and enter its root directory.
2. Follow [the setup guide](phase-1-setup.md) to create the Python environment, install locked Python/npm dependencies, configure PostgreSQL and install Exasol Personal. Use the dedicated application database user and a certificate obtained from the trusted local deployment. Keep private credentials outside Git.
3. Once both stores are configured, run the following commands sequentially:

```powershell
. .\scripts\env.ps1
.\.venv\Scripts\python.exe -m advergent.worker migrate
.\.venv\Scripts\python.exe -m advergent.worker probe
.\.venv\Scripts\python.exe -m advergent.worker refresh
.\.venv\Scripts\python.exe -m advergent.worker commerce
.\.venv\Scripts\python.exe -m advergent.worker ads
.\.venv\Scripts\python.exe -m advergent.worker attribution
.\.venv\Scripts\python.exe -m advergent.worker finance
.\.venv\Scripts\python.exe -m advergent.worker inventory
.\.venv\Scripts\python.exe -m advergent.worker diagnostics
.\.venv\Scripts\python.exe scripts/export_openapi.py
npm.cmd run types --prefix frontend
npm.cmd run build --prefix frontend
.\.venv\Scripts\python.exe -m uvicorn advergent.api:create_app --factory --host 127.0.0.1 --port 8000
```

4. Open http://127.0.0.1:8000 and sign in using the locally configured operator password. Inspect the golden metric, module evidence, cohort coverage, budget and unified decisions. Historical fixture evidence intentionally produces stale-data warnings and abstentions.
5. Run isolated tests with `.\.venv\Scripts\python.exe -m pytest -q`. Real-store regression requires dedicated configured stores and explicit `RUN_INTEGRATION=1`; use `.\.venv\Scripts\python.exe -m pytest -q --ignore=backend/tests/test_execution_integration.py -x`. Remove the integration environment variable afterward. The excluded execution suite creates simulated approvals/actions and is unnecessary for this non-mutating reproduction path.

Existing deployments must retain their private configuration, trusted TLS certificate, launcher state, database volumes and audit history. The fresh-install steps in the setup guide must not be used to replace an existing deployment. Detailed preserving rehearsal/recovery instructions are in [the demo runbook](phase-14-demo.md).

## Data sources and licence information

All demonstration business records are synthetic project fixtures, not real merchant/customer data, scraped datasets or live platform exports. They cover commerce, Meta/Google-shaped reporting, mappings/click claims, expenses/settlements/returns, warehouse observations, destination/creative observations and funnel events. Fixtures are in [fixtures](../fixtures/); deterministic generators are in `backend/advergent/*_fixture.py`.

The repository has an MIT licence and no separate fixture licence was found. The bundled project-authored fixtures are distributed with the project under that repository licence. Exasol Personal and third-party dependencies retain their own licences and applicable terms; the project's MIT licence does not relicense them. Shopify, Meta and Google references describe synthetic data shapes, not affiliated or certified integrations.

## APIs and third-party tools

| Tool/API | Use |
|---|---|
| Exasol Personal / PyExasol | Real analytical SQL storage, querying and reconciliation |
| PostgreSQL / SQLAlchemy / psycopg | Operational persistence, publication control, sessions and audit history |
| Python / FastAPI / Uvicorn | Backend, authenticated local REST API and workers |
| React / TypeScript / Vite | Browser interface |
| OpenAPI / openapi-typescript | API schema and generated client types |
| pytest / HTTPX / Playwright / Chrome | Isolated, real-store, API and browser verification |
| Podman / Exasol Personal launcher | Local database deployment |

Runtime dependencies are pinned in `requirements-lock.txt` and `frontend/package-lock.json`. No live Shopify, Meta or Google API, external model API, paid API or cloud service is required by the demonstrated runtime. Any development-assistance disclosure required by the event should be supplied separately according to its rules.

## Demonstration video and supporting materials

**Video URL: [ADD AN ACCESSIBLE RECORDING LINK BEFORE SUBMISSION]**

No submission video was found in the repository. Confirm the event's required duration and format; the sequence below is a proposed recording outline, not an official requirement:

1. Explain the merchant problem and Track 02 fit.
2. Show the authenticated app, synthetic-data labels and real Exasol foundation calculation.
3. Show financial cost coverage, inventory/size risk and first-party channel attribution.
4. Show separate cohort maturity/history coverage and sparse-demand abstention.
5. Query budgets and unified decisions; explain fixed-total constraints, inventory precedence and explicit approval requirements. Do not create or execute an advertising action for the recording.
6. Show preserved prior-publication evidence and conclude with current limitations.

Supporting materials: [architecture](architecture.md), [setup](phase-1-setup.md), [acceptance evidence matrix](phase-14-evidence.md), [demo runbook](phase-14-demo.md), [Phase 13 verified handoff](handoffs/phase-13.md), [Phase 14 current handoff](handoffs/phase-14.md), and `openapi.json`.

Before submission, insert the accessible video link, confirm the complete source/docs/fixtures are accessible on GitHub, and update gate status only from completed verification. The recorded project deadline of October 30, 2026 at 23:59 IST has passed; this draft is dated October 31 and does not establish event eligibility or a deadline extension.
