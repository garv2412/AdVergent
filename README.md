# AdVergent
Unified advertising, sales, and inventory intelligence that turns fragmented commerce data into actionable recommendations.

## Hackathon submission

**Track 02 — Customers, Channels & Demand**

Apparel merchants compare advertising, sales and inventory in separate reports. Revenue can look healthy while returns, cash-on-delivery failures, missing costs or unavailable sizes make additional spending unsafe. AdVergent brings those signals into one evidence-based decision workspace.

The working local prototype uses **real Exasol Personal analytics**, project-authored synthetic data and approval-required simulated advertising actions. It has no live Shopify, Meta or Google connection.

### Submission materials

| Required material | Location and status |
| --- | --- |
| Source code | [Backend](backend/), [frontend](frontend/), [migrations](migrations/) and [synthetic fixtures](fixtures/) |
| Pitch deck | [Editable PowerPoint](docs/submission/AdVergent-pitch-deck.pptx) and [readable text companion](docs/submission/pitch-deck.md) |
| Demo video link | **Pending: an accessible recording URL must be added before confirming submission completeness** |
| Setup and run instructions | [Reference environment and database setup](docs/phase-1-setup.md), [ordered application reproduction](docs/hackathon-submission.md#setup-and-reproduction) and commands below |
| Problem statement, data and third-party disclosures | [Submission description](docs/hackathon-submission.md) |
| Demonstration sequence | [Recording guide](docs/submission/demo-video.md) and [operator runbook](docs/phase-14-demo.md) |
| Licence | [MIT](LICENSE). Upstream tools retain their own terms. |

### What the application does

- Reconciles channel spend and first-party attribution with commerce contribution, returns and COD/RTO costs.
- Shows first-delivered-purchase cohorts with separate mature/immature windows and missing-cost coverage.
- Combines demand signals with inventory cover and size availability, with conservative breakout and budget scenarios.
- Resolves conflicting recommendations, preserves fixed budget totals and explains stale-data or insufficient-evidence abstentions.
- Retains approvals, simulated action read-back and recommendation history. Every simulated advertising change requires exact explicit approval.

### Exasol and application architecture

Exasol Personal stores and queries typed analytical evidence through encrypted, certificate-verified PyExasol connections. PostgreSQL stores sessions, jobs, publication pointers and audit state. Python/FastAPI serves the React/TypeScript interface. The application does not substitute fixture answers for unavailable Exasol analytics.

The bundled commerce fixture has 30 products, 180 variants, 1,000 synthetic customers and 3,000 orders. No real customer data or live advertising credentials are required. Deterministic generators live in `backend/advergent/*_fixture.py`.

### Local setup and run

The documented reference host uses Windows/PowerShell, Python 3.14, Node.js 24, PostgreSQL 17.9, Podman and Exasol Personal launcher 2.3.0. Fresh-machine reproduction remains unverified.

```powershell
git clone https://github.com/garv2412/AdVergent.git
cd AdVergent
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
npm.cmd ci --prefix frontend
```

Follow [database and private configuration setup](docs/phase-1-setup.md#local-databases-and-private-configuration) before running the application. Configure a dedicated Exasol application user and trust the certificate obtained from your local deployment. Existing installations must preserve credentials, launcher state, volumes and audit history.

With both configured stores running, execute sequentially:

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

Open `http://127.0.0.1:8000` and sign in with your configured operator password. Default fixture evidence is historical, so stale-data warnings and abstentions are expected. The separate foundation example should show INR 4,000 sales and INR 300 contribution after ads.

Isolated tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Real-store and browser reproduction, including the non-mutating suite boundaries, is documented in the [submission guide](docs/hackathon-submission.md#setup-and-reproduction) and [demo runbook](docs/phase-14-demo.md). Keep `.env`, `.runtime`, credentials and local database state outside Git.

### Verification scope

Phases 1–13 have documented synthetic local gates using actual Exasol/PostgreSQL. Phase 14 hardening remains in progress, with its final gate pending. [Recorded evidence](docs/handoffs/phase-13.md) and [current status](docs/project-status.md) distinguish isolated tests, actual-store tests and browser rendering substitutes. Live API fidelity, measured merchant benefit, calibrated predictions and production readiness remain unverified.

## Project documentation

- [Project rules and phase workflow](AGENTS.md)
- [Current status](docs/project-status.md)
- [Product specification](docs/product-specification.md)
- [Architecture](docs/architecture.md)
- [Phase plan](docs/phase-plan.md)
- [Phase 14 demo hardening runbook](docs/phase-14-demo.md)
- [Included acceptance evidence matrix](docs/phase-14-evidence.md)
- [Current handoff: Phase 14 demo hardening](docs/handoffs/phase-14.md)
- [Phase 7 diagnostics handoff](docs/handoffs/phase-7.md)
- [Phase 8 approved execution handoff](docs/handoffs/phase-8.md)
- [Phase 9 clearance handoff](docs/handoffs/phase-9.md)
- [Phase 10 breakout handoff](docs/handoffs/phase-10.md)
- [Phase 11 cohort handoff](docs/handoffs/phase-11.md)
- [Phase 13 unified decisions handoff](docs/handoffs/phase-13.md)
- [Unified decisions contract](docs/phase-13-decisions.md)
- [Phase 12 budget optimization handoff](docs/handoffs/phase-12.md)
- [Budget optimization contract](docs/phase-12-budget.md)
- [Cohort contract](docs/phase-11-cohorts.md)
- [Breakout contract](docs/phase-10-breakout.md)
- [Clearance contract](docs/phase-9-clearance.md)
- [Approved-execution contract](docs/phase-8-approved-execution.md)
- [Foundation setup and verification](docs/phase-1-setup.md)
- [Commerce mirror contract and commands](docs/phase-2-commerce.md)
- [Ad reporting contract and commands](docs/phase-3-ad-reporting.md)
- [Mapping/attribution contract and commands](docs/phase-4-mapping-attribution.md)
- [Finance contract and commands](docs/phase-5-finance.md)
- [Inventory contract and commands](docs/phase-6-inventory.md)
- [Diagnostics contract and commands](docs/phase-7-diagnostics.md)
