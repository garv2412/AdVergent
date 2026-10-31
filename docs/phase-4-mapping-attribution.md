# Phase 4 mapping and attribution contract

Implemented October 30, 2026 over synthetic evidence, real local PostgreSQL and real TLS-pinned Exasol. Accepted requirements are ambiguity abstention, multi-product relationships, provenance/confidence/validity/overrides, versioned first-party attribution, separate platform reporting, retained unattributed orders and reconciled allocations. All numerical policies below are implementation defaults, not individually confirmed merchant preferences. No live platform, advertising mutation, full finance or later-phase module is included.

## Mapping semantics

[Source models and importer](../backend/advergent/attribution.py) accept explicit reviewed product sets scoped to exact platform/account/resource IDs. Each candidate retains ID, product IDs, provenance, confidence in integer basis points, half-open validity interval `[valid_from, valid_to)`, actor, reason and override flag. Unknown commerce products, accounts/resources, duplicate IDs/products and invalid dates reject. Native advertising product references remain unverified hints and never create mappings. Names do not establish identity. No automatic parent/child inheritance or narrow advertising capability is invented.

At a specified evaluation time, active explicit overrides take precedence. Conflicting override product sets abstain. Without overrides, candidates with confidence at least 9,000 basis points qualify. One distinct complete product set resolves; multiple distinct sets abstain as ambiguous; none remain unmapped. Agreeing evidence may corroborate the same set. Multi-product sets are indivisible relationships, not competing single-product candidates. Override confidence remains visible but does not veto an explicit reviewed override. Overlap is permitted so conflicts remain visible rather than silently selecting one record.

The published relationship view evaluates at the attribution fixture's `observed_at`, exposed separately as `mapping_as_of`. Historical validity is preserved in full evidence; the reusable resolver accepts any aware timestamp. Freshness uses the oldest observation across mapping/click, commerce and ad inputs, not publication time. No relationship validity is inferred from spend coverage. The current synthetic ad hierarchy is a snapshot, not a historical live hierarchy service.

Mapping/override edits use a new immutable complete JSON source with `worker attribution --fixture PATH`. PostgreSQL retains each exact configuration snapshot, input IDs, run/attempt state and publication pointer. The worker is the trusted local configuration path; there is no browser mutation/editor or approval system in Phase 4. This is an operational catalog mapping change, with no advertising write. Published analytical mapping evidence and decisions are copied to Exasol. No operational analytics fallback exists.

## First-party model and allocation

`last-paid-click-7d-no-view-v1` implements the documented proposed default: latest identifiable paid click in the inclusive seven-day interval ending at order placement. Explicit synthetic order/event linkage represents first-party identity; no cookie, consent, tracking instrumentation or live identity-resolution claim is made. Views, organic/unidentifiable clicks, post-order clicks and older clicks are ineligible. Click IDs deduplicate identical delivery; conflicting same-ID evidence rejects. Unknown order/resource references reject. Event time, not delivery/list order, determines attribution. Campaign identity is platform/account/campaign ID from the pinned hierarchy.

Latest-time events within one campaign assign once; ties across campaigns abstain. Orders without eligible clicks or with ambiguous ties retain a single unattributed assignment with reason/evidence. Product mappings never fabricate acquisition evidence or restrict a customer's purchased products. All placed orders, including cancelled/RTO/undelivered, remain in the order universe; displayed amounts are placed merchandise, not recognized revenue or contribution.

Each order has exactly one row in an enabled Exasol primary key. Actual Exasol joins allocate every purchased line to that order's campaign or unattributed bucket. Product allocations follow the purchased variant's commerce product, never the advertised set. Exact integer paise use `quantity * unit_price - discount`, excluding separately stored tax. No proportional split or rounding is needed because the whole order has one campaign and every line joins once. Counts and paise reconcile independently to the pinned commerce totals; product allocation sums reconcile to line allocation; every refund joins back to the original order/campaign while retaining its actual refund date. No refund financial recognition, costs, reserves, contribution, ratios or cohort/LTV module is calculated here. Phase 5 must apply these assignments to actual line economics and preserve reconciliation.

Synthetic platform claims have a separate typed collection and UI view. Both Meta and Google claim the same example order. Claims do not enter first-party assignment, order value or allocations; they are not evidence of external API report compatibility or incremental effect.

## Storage, publication and recovery

[Migration 004](../migrations/004_attribution.sql) adds separate PostgreSQL runs, attempts and singleton publication. The worker acquires the existing commerce/ad advisory locks and an attribution lock, pinning inputs throughout publication. Missing/unavailable inputs fail. UUID derives from exact fixture SHA-256, normalization namespace `attribution-v1:` and both upstream dataset IDs. Selecting a different model/input requires a different supported version; unsupported models reject. Successful replay preserves original completion and source dates. The next lock holder marks interrupted running attempts failed.

[Exasol adapter](../backend/advergent/attribution_sql.py) owns transactional mapping/evidence payloads, typed order assignments and a completion marker containing the commerce input ID. Full read-back, typed/source comparison and analytical reconciliation precede PostgreSQL publication. An actual SQL failure rolls back all three tables; failed verification preserves the prior pointer. Failure after analytical commit leaves an immutable orphan that retry verifies and reuses. No cross-store transaction, cleanup, hard-kill/reboot guarantee or large-source capacity claim is made.

Authenticated `GET /api/attribution` returns typed analytical data, model, input IDs, source time/age, mapping evaluation time, hash/version, publication/query timestamps and latest attempt status. `dependencies_current=false` labels retained historical inputs when upstream pointers change. It never silently joins the new commerce/ad publication. Exasol unavailability suppresses all mappings/allocations/claims and current query time while retaining publication evidence. Operational failures remain sanitized 503. The UI clears prior values on query/error and renders all source fields as text.

## Commands and evidence

```powershell
. .\scripts\env.ps1
.\.venv\Scripts\python.exe -m advergent.attribution_fixture
.\.venv\Scripts\python.exe -m advergent.worker migrate
.\.venv\Scripts\python.exe -m advergent.worker attribution
.\.venv\Scripts\python.exe -m advergent.worker attribution --fixture fixtures/attribution-v1.json
$env:RUN_INTEGRATION='1'
.\.venv\Scripts\python.exe -m pytest -q
Remove-Item Env:RUN_INTEGRATION
.\.venv\Scripts\python.exe scripts/export_openapi.py
npm.cmd run types --prefix frontend
npm.cmd run build --prefix frontend
$env:E2E_OPERATOR_PASSWORD=(Get-Content -Raw .runtime/operator-password.txt).Trim()
npm.cmd test --prefix frontend
```

Browser checks require the existing real API and private stores/password environment. The Phase 4 healthy test imports/replays the default source and deliberately fails a genuine SQL insert, then restores default attribution in `finally`. Never run healthy imports while Exasol is stopped. Outage mode uses the existing launcher `stop --deployment advergent`, `E2E_DATABASE_FAILURE=1`, the same browser suite, and launcher `start --deployment advergent` in `finally`; restore healthy mode and probe/replay existing publications afterward. No certificate bypass, new resources or charges are needed. Exact executed results: [Phase 4 handoff](handoffs/phase-4.md).

## October 30 Phase 5 extension

The later [finance contract](phase-5-finance.md) consumes these immutable assignments and pinned upstream IDs. It assigns actual line contribution and dated refund/recovery economics exactly once, including unattributed orders. Platform claims and placed merchandise remain distinct from delivered finance and incremental profit. Phase 4's original handoff remains historical; it did not verify financial contribution.


## October 30 Phase 6 consumer clarification

Phase 6 now re-evaluates retained reviewed mapping evidence at actual eligibility evaluation time, including validity, confidence, ambiguity and overrides. It does not inherit mappings or infer product controls. Changed upstream IDs block eligibility. See [inventory contract](phase-6-inventory.md).


## October 30 Phase 7 consumer clarification

Phase 7 resolves pinned reviewed mappings at actual evaluation time before creative suggestions. Low-confidence/ambiguous/unmapped/expired relationships withhold suggestions; native hints never become scope. All destinations must belong to the complete exact reviewed set. No control or advertising write follows from a mapping. See the [diagnostics contract](phase-7-diagnostics.md).


## October 30 Phase 8 consumer clarification

The separately authorized [approved execution module](phase-8-approved-execution.md) consumes exact reviewed whole-resource/member scope, capabilities and current coherent analytical evidence. Every simulated pause, throttle, transfer, resume or inverse recovery requires its own durable exact explicit approval and actual-clock revalidation. Imported prior-pause evidence is never an execution ledger or approval. Recommendations remain advisory; no live API capability or mutation is established. Phase 8 gate evidence is recorded separately in its handoff. Earlier module boundaries remain historical.
