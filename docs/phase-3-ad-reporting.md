# Phase 3 ad reporting contract

Implemented October 30, 2026 for deterministic source simulations. Accepted boundaries remain INR, Asia/Kolkata reporting, real Exasol analytics, PostgreSQL operational state, INR 0 infrastructure/API charges, and approval for every future advertising mutation. This implements application contracts, not Meta/Google SDK, sandbox or live API compatibility. No network advertising APIs or advertising mutation methods exist.

## Source and normalization

[Source models and importer](../backend/advergent/ads.py), [fixture generator](../backend/advergent/ads_fixture.py), [initial fixture](../fixtures/ads-initial-v1.json) and [corrected fixture](../fixtures/ads-corrected-v1.json) implement a small hand-calculated scenario. Seed 20261030, scenario clock October 30 at 10:00 UTC, two synthetic accounts, 16 hierarchy resources and five distinct budgets. Counts, half-hour grain and freshness threshold are implementation defaults, not separately confirmed merchant preferences.

Each fixture contains a complete bounded history of source report revisions. It is independently importable; it is not a delta requiring the previously published fixture. Account currency is INR. Meta input amounts are decimal rupee strings with at most two fractional digits; Google input amounts are integer micros divisible by 10,000. Normalization uses exact integer paise. Floats, foreign currencies, negative amounts and sub-paise inputs are rejected; there is no currency conversion or implicit rounding policy. A live adapter must establish its own precision/aggregation contract.

Source reporting uses closed half-hour intervals aligned to UTC minutes 00/30. This is a deliberately synthetic interval contract, not a claim that either external API exposes this grain. UTC and Asia/Kolkata both align to these intervals, so no bucket crosses the India day boundary. `source_day` must equal the interval start date in the configured account timezone. Interval start and normalized report observation timestamps are stored as UTC strings; the explicit reporting date is derived in Asia/Kolkata. An interval starting October 29 at 18:30 UTC belongs to October 30 in India while retaining October 29 as the Google UTC source day. Unaligned intervals and naive/future source observations are rejected. No approximate apportionment of foreign-timezone daily totals occurs.

The additive report key is platform + account ID + resource ID + UTC interval start. Currency, grain and absence of attribution/breakdown dimensions are fixed by this schema. Only Meta/Search ads, Shopping-like ad groups and PMax-like asset groups report spend. Parent totals cannot enter the same additive dataset. Stable IDs, not names, establish identity; resource/account identities are scoped by platform/account. Shared budget amounts are metadata, never summed as spend.

For each report key, higher revision replaces the entire previous amount, including a correction to zero. Identical revisions deduplicate, older revisions cannot overwrite newer reports, and equal revisions with different content reject the fixture. A delayed new interval adds one grain. Missing intervals mean not reported in this bounded source; they do not imply zero spend or live-source completeness. No cumulative daily snapshots are appended to hourly facts.

Independent oracles: initial six grains total **290,021 paise**. The correction replaces 10,001 with 9,001 paise, replaces 80,006 with zero, and adds a delayed 1,007-paise interval: seven grains total **210,022 paise**. Corrected Meta is 30,010 and Google 180,012 paise. India dates October 29/30 total 59,004/151,018 paise. The shared Google budget's two campaigns total 110,007 paise.

## Hierarchy and capability scenarios

| Scenario | Ownership and visible limits |
|---|---|
| Meta ad-set-owned budget | Campaign -> ad set -> product-linked ad; ad set owns budget; campaign has no invented effective budget and exposes affected descendant budget IDs |
| Meta campaign-owned budget | Campaign owns budget inherited by ad set and mixed-product ad; broad resource scope is visible |
| Google Search shared budget | Two campaigns, each with ad group/ad, reference one separate budget resource; both members and shared impact are visible |
| Google Shopping-like multi-product group | Campaign -> multi-product ad group; separate nonshared budget resource |
| Google PMax-like multi-product resource | Campaign -> asset group; its nonshared budget is distinct from the Search shared-budget scenario |

`source_product_refs` are native synthetic hints only. They are deliberately not Shopify product IDs, verified mappings, provenance/confidence decisions or attribution. Scope consistency is validated (one hint for single, two or more for multiple, none for unknown). Resolving those hints to commerce belongs to Phase 4.

Resource responses expose parent, campaign, status, effective budget/owner, affected budgets, shared members, source product scope/hints and capability evidence. Synthetic status controls are described as supported; resource budget control belongs only to an owning Meta campaign/ad set. Google budget capability belongs to its separate budget resource, including shared-budget membership/impact. All budgets expose approval-required and mutation-disabled flags. Every product-level control is unsupported and advisory-only. No broad pause is proposed from a product's condition. No capability label authorizes a write. Real external capabilities remain unverified and must be rediscovered by a later live adapter.

## Operational and analytical publication

[PostgreSQL migration](../migrations/003_ad_reporting.sql) owns ad runs, attempts, platform cursors, revisioned source staging and an independent advertising publication pointer. `MetaReportingAdapter` and `GoogleReportingAdapter` persist page progress and source revisions under a single advertising advisory lock. Each page's state and cursor commit together. Duplicate/late reports are stable. Retry skips committed pages and reconstructs the full expected latest-revision set before loading. Validation rejects malformed fixtures before creating a run/attempt.

Run UUID is derived from SHA-256 of exact fixture bytes with the `ads-schema-v2:` normalization namespace. Whitespace changes create another version. Selecting a historical fixture explicitly may republish historical evidence; this does not make it fresh. Attempts are individually audited. Interrupted running attempts are marked failed by the next lock holder. Successful replay preserves original completion and source observation timestamps.

[Exasol adapter](../backend/advergent/ads_sql.py) owns all vendor SQL. `AD_ENTITIES` retains normalized account/hierarchy/budget capability payloads, `AD_RESOURCES` holds typed identity/campaign/budget relationships, and `AD_REPORTS` holds typed spend/reporting date plus normalized provenance. A transactional completion marker gates read-back. Full source/core verification and actual Exasol aggregation precede PostgreSQL publication. Campaign/day/budget spend comes from an Exasol join and aggregate, with separate whole-dataset count/sum reconciliation. There is no PostgreSQL analytical fallback.

Failed SQL loads roll back entities, resources, reports and marker. Failed import/verification leaves the prior pointer intact. A commit followed by failure before publication leaves an immutable orphan; retry reuses and verifies it before publishing. There is no cross-database transaction, automatic version/staging cleanup or high-availability guarantee.

## Authenticated query and freshness

`GET /api/ads` uses existing server-side operator authentication. It returns one consistent published dataset's Exasol totals, campaign/day groups, normalized reports, hierarchy and capabilities. Dataset ID/version, SHA-256, source observation, scenario clock, completion time, query-start time and latest attempt status accompany the response. This small fixture response is bounded by source size; no production pagination/performance claim is made.

Source observation applies to the complete two-adapter fixture snapshot. Freshness is its wall-clock age with a 900-second default; import/replay never resets it. Historical fixtures intentionally display stale. Exasol errors return `analytics_unavailable`, null data and query time, unknown current freshness, and retained source/publication evidence. Operational database errors return sanitized 503. UI clears prior values when a query starts or fails and shows failed attempts alongside the last complete publication. Capability payloads disappear with analytical unavailability rather than falling back to operational staging. Foundation contribution remains its separate two-line golden fixture.

## Commands

From repository root, retaining existing private configuration/certificate and volumes:

```powershell
. .\scripts\env.ps1
.\.venv\Scripts\python.exe -m advergent.ads_fixture
.\.venv\Scripts\python.exe -m advergent.worker migrate
.\.venv\Scripts\python.exe -m advergent.worker ads --fixture fixtures/ads-initial-v1.json
.\.venv\Scripts\python.exe -m advergent.worker ads
.\.venv\Scripts\python.exe -m advergent.worker ads
$env:RUN_INTEGRATION='1'
.\.venv\Scripts\python.exe -m pytest -q
Remove-Item Env:RUN_INTEGRATION
.\.venv\Scripts\python.exe scripts/export_openapi.py
npm.cmd run types --prefix frontend
npm.cmd run build --prefix frontend
$env:E2E_OPERATOR_PASSWORD=(Get-Content -Raw .runtime/operator-password.txt).Trim()
npm.cmd test --prefix frontend
```

The browser ad test itself imports initial/corrected fixtures, induces a genuine SQL duplicate-key failure, and finally restores the default corrected publication. It inherits private database settings from the environment; never print them. For an actual outage, stop the existing Exasol deployment with the pinned launcher, set `E2E_DATABASE_FAILURE=1`, run the same suite, then restore Exasol in `finally`, remove the flag and run healthy checks. Exact results and limitations belong to the [Phase 3 handoff](handoffs/phase-3.md).

No live authentication/reporting, advertising mutations, mapping/attribution, recommendations, full finance, later-phase modules or cloud resources are part of Phase 3. Existing metric/action/approval contracts remain in force.


## October 30 Phase 6 consumer clarification

Phase 6 reads exact resource status/budget ownership capabilities and shared members for advisory inventory eligibility. Unsupported narrow product controls keep mixed-product advice advisory; neither a product mapping nor a stockout creates a platform capability. Every mutation still requires approval; no writes exist. See [inventory contract](phase-6-inventory.md).


## October 30 Phase 7 consumer clarification

Phase 7 displays exact status/product-control capability evidence and shared-budget members with advisory diagnostics. Fixed creative review suggestions do not assert an edit capability, narrow mixed-resource control or authorization. No reporting source is mutated. See the [diagnostics contract](phase-7-diagnostics.md).


## October 30 Phase 8 consumer clarification

The separately authorized [approved execution module](phase-8-approved-execution.md) consumes exact reviewed whole-resource/member scope, capabilities and current coherent analytical evidence. Every simulated pause, throttle, transfer, resume or inverse recovery requires its own durable exact explicit approval and actual-clock revalidation. Imported prior-pause evidence is never an execution ledger or approval. Recommendations remain advisory; no live API capability or mutation is established. Phase 8 gate evidence is recorded separately in its handoff. Earlier module boundaries remain historical.
