# Phase 2 commerce mirror

Implemented October 30, 2026 for the synthetic single-merchant demo. This is a fixture adapter, not a Shopify SDK, webhook endpoint, sandbox test or live integration.

## Source contract

[Source models and importer](../backend/advergent/commerce.py) validate full source records for products, variants, synthetic customers, orders, order lines, refunds and one warehouse's inventory. IDs are stable within each collection. Money is integer paise; orders are domestic INR. Timestamp inputs require explicit offsets and retain event times separately from order placement/refund dates. The source snapshot observation and scenario clock are fixed and cannot be in the future.

Catalog variant costs and historical order-line costs are separate values, with source, effective date and actual/estimated/missing status. Missing costs stay null. Payment method, payment status and fulfillment status are separate: delivered/unremitted COD, prepaid/shipped, cancellation and RTO remain distinguishable. Refunds retain original order/line links, quantity, tax, event date and inventory-recovery status; they do not automatically restock inventory. Reconciliation validates references, refund quantity/merchandise limits and complete single-warehouse variant inventory coverage.

The current generator uses the proposed engineering defaults: seed 20261030, 180-day history, 30 products, 180 variants, 1,000 customers and 3,000 orders. The fixed scenario/observation clock is October 29 at 18:00 UTC. These are implementation defaults, not newly confirmed user requirements. The fixture also has 3,600 lines, 143 refunds, stockouts, an archived product, repeat customers and untrusted catalog text. No financial dashboard results are embedded in this source.

## Import and reconciliation

Each fixture's SHA-256 plus commerce schema version determines an immutable dataset/run ID. One PostgreSQL advisory lock serializes commerce imports; foundation refresh uses its existing separate lock. PostgreSQL owns import state, delivery receipts and temporary source staging. Staging is operational recovery input, never an analytical query fallback.

Each source page commits its receipts, staged changes and next-page cursor in one PostgreSQL transaction. Repeated delivery IDs with the same content are ignored; reused IDs with different content fail. A newer source timestamp replaces an older version. An older version cannot resurrect a tombstone. Equal timestamps with different content fail rather than choosing an arbitrary winner. The next worker labels interrupted running imports failed and resumes the same fixture's durable cursor. Invalid pages do not advance the cursor.

After every page is durable, the complete authoritative fixture snapshot replaces staging atomically. This repairs missed creates/updates and sweeps absent records, including missed deletes. Snapshot duplicates, dangling relationships, incomplete warehouse coverage or regressions/conflicts against delivered revisions prevent publication. This sweep is valid only for a complete fixture snapshot: future live pagination must establish snapshot completeness and handle changes during traversal. No such live guarantee is claimed here.

The [Exasol adapter](../backend/advergent/commerce_sql.py) loads typed core tables plus exact source payloads transactionally in batches of 100 records. A completion marker commits with all seven tables. Full read-back compares every payload and its typed core columns before PostgreSQL publication. Failed loads roll back and retain the prior complete publication. A crash after analytical commit can resume by verifying that immutable dataset, then publishing; there is no cross-database transaction. Successful replay verifies/reuses the existing run and creates a separate operational attempt audit record, preserving the dataset's original completion time. Changing fixture bytes creates a new run, not a continuation of another source file. Old analytical versions and source staging are retained; cleanup is deferred.

## Queries, freshness and UI

Authenticated `GET /api/commerce` reports real Exasol counts, quantities, placed merchandise value excluding explicit tax, refund merchandise amounts, missing-cost counts and delivered-line joins. Placed value is an ingestion reconciliation total, not recognized sales, contribution or attribution. Financial recognition remains Phase 5.

Authenticated `GET /api/commerce/records/{kind}?dataset_id=...&limit=25&offset=0` returns source records from Exasol, with a maximum page size of 100. Dataset pinning rejects a changed publication with 409. The UI offers all seven collections, page controls and escaped field inspection. Foundation financial cards remain the separate two-line golden dataset; they are not totals for these 3,000 orders.

Freshness uses wall-clock age of the complete source observation, never import completion or query time. The 900-second threshold reuses the proposed inventory execution-freshness default and is reported explicitly in the response, not a proven universal policy. It is currently an implementation constant; broader configurable recommendation policies belong to later phases. A historical fixture is intentionally stale after replay. Exasol failure returns unavailable with unknown freshness, no totals and no successful query timestamp; source/publication evidence remains. A failed import shows checkpoint progress and retains prior publication. No dependent action system exists yet.

## Local commands

Reuse the private local environment and existing stores from [Phase 1 setup](phase-1-setup.md); do not regenerate credentials or volumes.

```powershell
. .\scripts\env.ps1
.\.venv\Scripts\python.exe -m advergent.commerce_fixture
.\.venv\Scripts\python.exe -m advergent.worker migrate
.\.venv\Scripts\python.exe -m advergent.worker commerce
# Explicit alternate immutable source, useful for controlled scenarios:
.\.venv\Scripts\python.exe -m advergent.worker commerce --fixture PATH_TO_FIXTURE
.\.venv\Scripts\python.exe -m uvicorn advergent.api:create_app --factory --host 127.0.0.1 --port 8000
```

Generating the fixture again is deterministic and replaces only `fixtures/commerce-v1.json`. The generator is local code, uses no API and incurs no infrastructure charge. Replaying a prior fixture can intentionally select that prior immutable publication; it does not make historical evidence current.

Verification, exact results, limitations and next-phase prerequisites are recorded in the [Phase 2 handoff](handoffs/phase-2.md).
