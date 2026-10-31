# AdVergent pitch deck

Text companion to [the editable PowerPoint deck](AdVergent-pitch-deck.pptx). Prepared October 31, 2026 IST.

## 1. AdVergent

Customer, channel and demand intelligence
for apparel merchants

Track 02 — Customers, Channels & Demand

A working local prototype with real Exasol Personal analytics, synthetic business data and approval-required simulated actions. Garv Gupta. October 31, 2026 IST.

Sources: docs/product-specification.md; Track name supplied by the submitter.

## 2. The merchant decision problem

Fragmented evidence can hide commercial risk

- **Reported revenue:** Returns, COD failures and missing costs change contribution.
- **Channel performance:** Overlapping platform claims complicate attribution.
- **Demand signals:** Product interest can coincide with unavailable key sizes.

The target scenario is a single Indian apparel merchant, one warehouse and domestic INR sales. These are the project problem assumptions, not findings from a merchant study.

Sources: docs/phase-0/README.md; docs/product-specification.md

## 3. One evidence-based decision view

Track 02 fit

- **Customers:** First-party attribution and mature 60/90-day contribution cohorts.
- **Channels:** Normalized spend, reviewed product mappings and contribution after ads.
- **Demand:** Deduplicated funnel signals, size availability and constrained budgets.

Cohort maturity, missing costs and incomplete history remain separate. Breakout ranking abstains when evidence is sparse or stale. Response assumptions are uncalibrated and do not establish causal benefit.

Sources: docs/phase-4-mapping-attribution.md; docs/phase-10-breakout.md; docs/phase-11-cohorts.md; docs/phase-12-budget.md

## 4. Exasol Personal powers the analytics

Actual SQL queries over versioned synthetic sources

- **Exasol Personal:** Typed analytical tables, joins, aggregates and reconciliation through PyExasol.
- **PostgreSQL:** Sessions, import jobs, publication pointers, approvals and retained audit history.
- **FastAPI + React:** Authenticated analytical endpoints and an operator workspace.

Encrypted certificate-verified Exasol connections. Workers publish only verified datasets. PostgreSQL supplies operational state, not a fallback analytical answer. The reference environment is a local Windows/Podman deployment.

Sources: docs/architecture.md; backend/advergent/exasol.py; docs/phase-1-setup.md

## 5. Inventory protection constrains advice

Recommendations expose their evidence and limits

- **Stockout or stale source:** Withhold unsupported growth and preserve resource scope.
- **Unknown costs or sparse history:** Keep contribution unknown and explain abstention.
- **Any simulated advertising change:** Require exact persisted approval, fresh revalidation and read-back.

Default unified decisions abstain on historical evidence. Inventory protection overrides growth, recovery and creative advice. No live Shopify, Meta or Google integration is implemented. The recording should not create or execute advertising actions.

Sources: docs/phase-6-inventory.md; docs/phase-8-approved-execution.md; docs/phase-13-decisions.md

## 6. A reproducible synthetic demonstration

Real databases with project-authored fixtures

- **3,000 orders:** 30 products, 180 variants and 1,000 synthetic customers.
- **INR 300 contribution:** Foundation: 4,000 sales − 2,200 COGS − 500 variable costs − 1,000 ads.
- **INR 11,000 per day:** Five default budgets preserve their exact total and remain frozen.

The two-line foundation arithmetic is separate from the full-commerce dataset. These values demonstrate implemented arithmetic and constraints. They are not measured merchant uplift. Default observations are historical/stale.

Sources: docs/product-specification.md; docs/phase-1-setup.md; docs/handoffs/phase-13.md

## 7. Verified behavior and remaining gaps

Recorded evidence as of October 31, 2026 IST

- **269 real-store passes:** Phase 13 broad non-mutating regression, plus a separate focused pass.
- **Healthy and actual outage:** Each Phase 13 browser run: 15 passed, 12 mode skips.
- **Current boundary:** Synthetic local scope. Live fidelity and production readiness remain unverified.

These are historical executed commands, not a new combined test run. Across browser modes there were 27 distinct cases, including two inherited rendering substitutes. Financial benefit, calibrated predictive accuracy, full history, production scale and hard-kill/new-host recovery remain unverified.

Sources: docs/handoffs/phase-13.md; docs/handoffs/phase-14.md

## 8. Run the prototype locally

Public source and reproducible inputs

- **Repository:** github.com/garv2412/AdVergent
- **Setup and run:** README.md and docs/phase-1-setup.md document dependencies and ordered imports.
- **Data and licence:** Project-authored synthetic fixtures under the repository MIT licence.

Python/FastAPI, React/TypeScript, PostgreSQL, Exasol Personal/PyExasol and Podman. Upstream products retain their own terms. Fresh-machine reproduction remains unverified. The project requires no paid API or live merchant credentials. The demonstration video and transcript are linked in README.md.

Sources: README.md; LICENSE; docs/phase-1-setup.md; docs/hackathon-submission.md
