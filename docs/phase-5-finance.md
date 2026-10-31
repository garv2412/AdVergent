# Phase 5 finance contract

Implemented for synthetic local management reporting on October 30, 2026. Gate evidence is in the [Phase 5 handoff](handoffs/phase-5.md). No statutory accounting, live source completeness or incremental profit is established.

## Requirements and implementation defaults

Accepted requirements: exact INR paise, historical cost provenance/effective dates, unknown missing costs, separate placed/delivered/cash amounts, actual refunds and COD/RTO, reserve replacement, negative contribution, undefined zero-spend ratios, unique pinned first-party allocation including unattributed orders, separate platform claims, real Exasol analytics and PostgreSQL operational state. Only Phase 5 is authorized; charges remain INR 0 and every future advertising mutation requires explicit approval.

Delivery-based recognition reuses the metric contract's implementation default. The source's historical line price excludes its explicit tax; discounts are already allocated to lines by commerce. Retained customer shipping is an explicit amount excluding tax. Tax-inclusive collection receivables and actual cash settlement never enter net sales. This is management contribution, not accounting net profit.

Reserve defaults are a 30-day delivery exposure window (exclusive maturity boundary), 1,000 basis point future return probability, 8,000 basis point inventory recovery and INR 50 additional return expense per exposed unit. These are visible synthetic assumptions, not merchant-confirmed rates or calibrated estimates. Calibration sample size is zero. Delivered orders/units, returned units, still-exposed units and mature remaining units are reported separately. Default fixture delivery occurs at placement for delivered records, an explicit instantaneous synthetic delivery convention; the commerce source itself has no delivery timestamp. Explicit later delivery evidence is supported and tested.

## Inputs and historical corrections

[Finance source](../backend/advergent/finance.py) is a complete immutable configuration/ledger: one expense, shipping, cash and delivery record per pinned commerce order; one explicit recovery assessment per refund; optional targeted historical cost corrections. INR comes from the pinned domestic commerce source. Unknown expense components or recovery values remain null. Every expense record has actual/estimated/missing status, source and effective date. Actual nonzero cash requires a settlement timestamp. Cash amounts represent the synthetic ledger's cumulative receipts/refunds at that timestamp; bank balances, accounts payable and payment-provider reconciliation are outside scope.

Use [generator](../backend/advergent/finance_fixture.py) to reproduce [finance-v1.json](../fixtures/finance-v1.json). This generates evidence, never dashboard totals. It reads the existing immutable commerce and corrected advertising fixtures. No catalog cost replaces a historical order cost. A correction names the exact line, replacement cost, actual/estimated status, source, reason and effective date at or before placement. It creates a new finance version and preserves the original commerce line and every prior publication. A later-effective correction rejects; changing today's variant cost has no automatic historical effect. Recovery cannot exceed the corrected historical cost of the refunded quantity. Unknown recovery does not become zero because a refund or an intact status exists.

All placed orders and lines are retained. The financial interval must contain the complete pinned order history; refund dates, delivery dates, financial effective dates and cash settlement dates must be valid within the snapshot. Connected ad intervals must fall inside the financial interval. The default financial as-of is October 30 at 10:00 UTC, matching corrected ad observation; commerce observation remains October 29 at 18:00 UTC. The oldest input observation determines freshness. Individual input observations remain visible. Replaying never renews source age.

The synthetic snapshot MER divides all net recognized sales in this complete input snapshot by its recorded Meta/Google spend. Those ad reports are a bounded seven-grain synthetic history, not evidence of continuous merchant spend coverage across 180 days. Differing cutoffs and stale source coverage are explicit in UI/API evidence. This descriptive snapshot ratio must not be presented as a complete live merchant-period MER. No inferred organic attribution, unreported spend, causal lift or platform gross-revenue multiplier enters finance.

## Line accounting and event dates

Exasol calculates:

- Net sales = delivered merchandise less recognized merchandise refunds plus explicitly retained shipping, all excluding tax.
- Net product cost = delivered historical COGS less explicitly recognized recovered inventory value plus failed-delivery damage/loss.
- Contribution before ads = net sales less net product cost less actual/estimated variable expenses.
- Contribution after ads = contribution before ads less actual connected recorded spend.
- POAS = contribution before ads / spend; connected-platform snapshot MER = net sales / spend.

Zero spend yields null ratios. Any unknown necessary line cost makes its contribution null and full affected contribution/POAS null. Line-count cost coverage, missing/estimated line counts and a covered-only contribution subtotal remain visible. The subtotal excludes incomplete lines and is not a full-store estimate, profit or conservative bound. Missing COGS on an undelivered item remains in historical evidence; sold COGS is correctly zero because no sale occurred. Known expenses and failed losses remain visible even without revenue.

Order shipping, variable expenses, losses and cash/receivables allocate by net placed line merchandise. Largest remainders receive residual paise; lexical line ID breaks ties. All-zero merchandise weights use equal weights. Source line discounts are not allocated twice. No binary floating-point ledger arithmetic is used; ratios are decimal strings and display may round them.

Prepaid captured but undelivered merchandise has no recognized sale. Delivered COD recognizes sales while tax-inclusive unpaid net collection remains unsettled. RTO recognizes no sold merchandise/COGS; intact stock is not charged again. Forward/reverse costs, fees and explicit damage/loss apply. Pre-shipment cancellation has no delivered sales and retains explicit incurred fees. Refunds reverse only delivered merchandise, retain actual event time and original acquisition assignment, and cannot prove recovery. A payment refund for an undelivered/cancelled/RTO order affects explicit cash settlement, with zero recognized merchandise reversal and zero sold-COGS recovery. A refund before the recorded delivery on an otherwise delivered line rejects as inconsistent evidence; split line fulfillment histories require a richer later source.

Separate Exasol transaction-day and acquisition-day summaries use Asia/Kolkata dates. Delivery recognizes sale/COGS, refund reverses merchandise on its actual date, recovery recognizes inventory value on its assessment effective date, expenses use ledger effective date and cash uses settlement date. Acquisition-day views move these same events back to placement day without duplicating them. Both sales/cash views reconcile to snapshot totals. Covered event subtotals can differ from covered line subtotals when one event of an otherwise known line is incomplete; coverage is explicitly labelled. Complete event and line contribution reconcile. These summaries are realized before ads; reserve and connected-spend ratios are snapshot views, not a daily ad attribution claim.

## Reserve replacement

Only delivered units inside the return window and not already refunded remain exposed. Expected incremental loss is probability times the nonnegative loss from the exposed merchandise allocation less assumed recoverable historical cost plus additional return expense. Integer rounding is explicit: recoverable cost rounds down to paise, probability loss rounds half up. Each line retains exposed units and reserve. A partial actual return removes only the returned units' reserve and records the actual refund/recovery/fees; remaining units retain exposure. A full outcome or maturity removes reserve. Unknown needed cost makes reserve unknown; no exposure or zero probability produces a known zero reserve.

Realized contribution contains known outcomes without future reserve. Expected contribution deducts the remaining reserve exactly once. Future loss is a synthetic assumption, not model-effectiveness evidence.

## Ownership, publication and UI

[Migration 005](../migrations/005_finance.sql) stores immutable complete configuration, input IDs, attempts and separate finance publication in PostgreSQL. Finance takes commerce, ads, attribution and finance advisory locks through publication. Attribution must match current upstream publications before import. The namespace `finance-v3:` hashes exact source bytes plus attribution ID (which includes its pinned commerce/ad IDs). Earlier development normalizations remain retained; they are not selected as defaults.

[Exasol adapter](../backend/advergent/finance_sql.py) stores unique line inputs with full provenance, typed dated events and a transactional completion marker. Exasol computes net economics, campaign joins, aggregates, date views and reconciliation. Every line joins one pinned first-party order assignment; actual purchased lines determine economics. Unattributed orders and spend-only campaigns remain present. Platform claims and the separate two-line foundation fixture never enter these totals. Line, order, placed value, sales, cash, expense/coverage, contribution and connected spend reconcile without duplicate assignment.

Full source/core/event read-back and reconciliation precede PostgreSQL publication. Real SQL failure rolls back lines/events/marker and retains prior publication. A failure after Exasol commit retains the prior pointer; replay verifies/reuses the orphan. Replay preserves original source/completion dates. No cross-store transaction, cleanup policy or hard-kill/reboot recovery guarantee is claimed.

Authenticated `GET /api/finance` exposes nullable typed totals, line and date evidence, financial allocations, source/hash/input IDs, freshness and latest attempt. Changed upstream inputs flag the retained pinned view; they never silently rejoin it. Actual analytics unavailability removes all current totals, allocations, lines, events and query time, retaining publication/assumption evidence. No PostgreSQL analytical fallback exists. [UI](../frontend/src/Finance.tsx) shows these distinctions, date views and paginated line provenance. Complete-source configuration changes use trusted local CLI; no browser editor, approval/execution module or advertising write exists.

## Commands

Load the existing private environment with `. .\scripts\env.ps1`, then:

```powershell
.\.venv\Scripts\python.exe -m advergent.finance_fixture
.\.venv\Scripts\python.exe -m advergent.worker migrate
.\.venv\Scripts\python.exe -m advergent.worker finance
.\.venv\Scripts\python.exe -m advergent.worker finance --fixture PATH
```

Use real authenticated checks and actual stopped-Exasol mode as recorded in the handoff. Healthy source-import tests require Exasol running and must run sequentially with other import checks. Always restore stores and default publications in `finally`. Preserve private environment, TLS pin, launcher state and persistent volumes. No new infrastructure/API or paid dependency is required.


## October 30 Phase 6 consumer clarification

Phase 6 pins this finance identity for nullable historical purchased-product expected contribution and a labelled daily contribution scenario. Missing product costs/history/demand leave estimates unknown; overlapping recommendation contexts cannot be summed. No incremental-profit or model-effectiveness claim follows. See [inventory contract](phase-6-inventory.md).

## October 31 Phase 9 consumer clarification

Clearance pins the coherent finance identity through inventory but evaluates prospective catalog COGS and explicit variable/return/holding assumptions. These never overwrite historical order costs, financial corrections/reserves or recorded spend. A scenario's after-additional-spend contribution is a what-if, not historical full finance or incremental profit. Missing required scenario costs remain null; COGS coverage is separate from variable/return/holding completeness. See [clearance contract](phase-9-clearance.md).
