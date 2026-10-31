# Phase 0 — Product contract and feasibility

Status: Phase 0 planning deliverable complete on 2026-10-27; runtime and live-platform verification are explicitly deferred execution gates.
Prepared: 2026-10-26. This phase creates planning documents only.

## 1. Agreed objective

Build a demonstrable, single-merchant prototype of AdVergent, designed to evolve into a SaaS product. Connect inventory, advertising performance, and contribution economics to explainable recommendations and approval-driven actions.

Deadline: **2026-10-30 at 23:59 Asia/Kolkata (IST)**.

The prototype must use real Exasol Personal calculations over synthetic data. Shopify, Meta, and Google connections and advertising mutations are simulated. Synthetic model results demonstrate behavior; they do not establish commercial effectiveness or integration compatibility.

## 2. Confirmed requirements

| Area | Agreement |
|---|---|
| Merchant | One Indian apparel brand with size/color variants and stocked inventory |
| Operations | One warehouse; domestic INR-only sales |
| Reporting | INR; Asia/Kolkata; UTC storage with explicit reporting conversion |
| Orders | Prepaid and cash on delivery (COD); returns and return to origin (RTO) |
| Inputs | Configurable taxes, costs, lead times, and policies |
| Platforms | Shopify sales; Meta and Google advertising |
| Analytics | Exasol Personal initially; replaceable through an adapter boundary |
| Changes | Explicit approval for every advertising change, including pauses and resumptions |
| Budget | INR 0 in infrastructure/API charges for the prototype |
| Hosting | Cloud trial credits acceptable only with charge prevention; local Exasol fallback allowed |
| Available systems | No platform accounts, historical data, or Exasol installation currently available |
| Deadline scope | End-to-end synthetic demonstration of all four pillars with simple predictive baselines |

## 3. Prototype user journey

1. Open the authenticated single-operator demo and see a persistent synthetic-data/simulated-actions label.
2. Inspect profitability and trace a metric to orders, costs, refunds, and advertising spend.
3. Trigger a predefined inventory or campaign scenario.
4. See an evidence-backed recommendation with confidence, freshness, and exact proposed changes.
5. Approve or reject it; no recommendation changes advertising state by itself.
6. Observe a simulated adapter execute, verify, and audit the change.
7. Exercise a partial failure and inspect the recovery state.
8. Reset the demo reproducibly without mixing different scenario runs.

## 4. Included behavior

| Pillar | Prototype implementation contract |
|---|---|
| Inventory | Days of cover, replenishment risk, weighted size-run availability, clearance scenarios |
| Financial | Contribution before/after ads, POAS, connected-platform MER, actual versus estimated costs, refunds, return reserves, COD/RTO |
| Predictive | Conservative budget scenarios, breakout scoring, mature 60/90-day cohort contribution; labelled synthetic baselines |
| Control/diagnostics | Approval inbox, simulated budget/status changes, partial failures, creative-fatigue signals, fixture-based destination/price checks |

The decision path must be real code operating on data, not hardcoded dashboard outcomes. Seeded source data and controlled failure injection are acceptable and required for reproducibility.

## 5. Explicitly deferred

- Live merchant onboarding, OAuth verification, developer-token/app-review approval, and real API mutations.
- Claims of incremental profit, validated LTV forecasting, or predictive accuracy on real merchants.
- Multi-merchant operation, billing, team roles, enterprise availability, and production security certification.
- Publishing campaigns, discounts, bundles, or AI-generated creatives.
- Multi-currency, international markets, multiple warehouses, backorders, and subscriptions.
- Tax filing/accounting compliance; configured tax amounts are demonstration inputs.
- Paid LLM/image-generation services; explanations use templates and existing synthetic catalog assets.

Deferred capabilities remain in the roadmap. None is implied to be validated by a simulated demonstration.

## 6. Proposed implementation defaults

These are engineering defaults, not additional user-confirmed requirements. Changes that affect cost, scope, external actions, or the deadline must be discussed.

| Component | Default |
|---|---|
| Frontend | React, TypeScript, Vite |
| Backend | Python, FastAPI, Pydantic |
| Analytics | Exasol Personal and PyExasol |
| Operational state | PostgreSQL, SQLAlchemy, Alembic |
| Processing | Explicit refresh jobs and PostgreSQL-backed job/action state; no Kafka/Redis requirement |
| Models | SQL feature calculation; Python/pandas/NumPy/SciPy only as needed |
| Explanations | Templates populated from persisted evidence |
| Testing | pytest for calculations/contracts; selected Playwright user journeys |
| Packaging | Separate frontend, API, and worker entry points in one repository |

Prefer a modular application over independent microservices for this deadline.

## 7. Database replacement boundary

Business services call typed operations such as inventory risk, campaign contribution, cohort contribution, and model-feature retrieval. They do not contain Exasol connection handling or vendor-specific SQL.

The analytics adapter owns connection setup, bulk loading, SQL dialect, schema migrations, transaction/publication semantics, and query implementations. Shared semantic definitions and fixtures specify required outputs. Exasol performs analytical joins and aggregations; the application must not bypass it with precomputed dashboard fixtures.

Replacement requires another adapter, data migration, semantic tests, and performance validation. Portability does not mean every database can be substituted without work. No second database adapter is required for the prototype.

PostgreSQL owns approvals, actions, jobs, settings, and simulated external state. A demo run ID and dataset version connect operational records with Exasol evidence. Failed or incomplete analytical refreshes must not appear as completed datasets.

## 8. Deployment and cost contract

- No paid resources, subscriptions, payment-enabled upgrades, or paid APIs without a new explicit agreement.
- A cloud provider qualifies only after verifying account eligibility, hardware compatibility, persistent storage, network requirements, and enforceable no-charge behavior.
- Billing alerts and an intention to shut down later are not sufficient charge prevention.
- Prefer trials that suspend service at credit exhaustion without paid conversion. Verify storage, egress, snapshots, addresses, and supporting resources are covered too.
- If charge prevention or compatible capacity is uncertain, use local Exasol. Availability must not depend on unverified free-tier claims.
- If Exasol runs locally, keep its database port private. A cloud frontend can call an authenticated application API through a suitable secured connection; availability then depends on the local machine. Do not expose the database directly.
- A local-only whole-application fallback is not yet agreed; discuss it if the cloud application plus local database topology is infeasible.
- AWS Free plan is the preferred conditional target; local Exasol is the fallback. Nothing has been provisioned. See the deployment decision for evidence and execution prerequisites.

## 9. Phase 0 exit status

Product objective, merchant scenario, budget boundary, approval policy, and deadline scope are settled. The metric and verification contracts are in the companion documents.

Phase 0 is complete at the planning/research level: user-provided AWS Free-plan evidence, versioned Exasol requirements, local prerequisite inspection, and a conditional deployment/fallback route are documented. This is not deployment clearance. Actual instance eligibility, IAM/quota, setup, connection, and load tests are mandatory Phase 1 gates. Live advertising checks remain a separate later milestone. See [deployment-decision.md](deployment-decision.md).

## Documents

- [Metric and business-rule contract](metric-contract.md)
- [Acceptance, feasibility, and delivery gates](verification-plan.md)
- [Deployment decision and prerequisite evidence](deployment-decision.md)
