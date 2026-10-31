# Metric and business-rule contract

Status: proposed defaults for the agreed synthetic prototype. All thresholds are configurable; none is represented as a universal retail benchmark.

## 1. Data and accounting conventions

- Store monetary values as decimals or integer paise; never binary floats for ledger arithmetic.
- Preserve explicit tax amounts. Report contribution excluding sales taxes, without assuming a universal GST rate or input-tax treatment.
- Allocate discounts and order-level costs to lines using a documented proportional basis, then allocate rounding residuals deterministically so totals reconcile.
- Keep event dates and original order dates. Offer transaction-date financial reporting separately from acquisition/order-cohort reporting.
- Retain cost source, effective date, actual/estimated/missing status, and currency.
- Missing costs remain unknown. Report coverage and incomplete contribution rather than silently treating them as zero.
- A newer unit cost does not rewrite historical orders unless an explicit historical correction is entered.
- Synthetic customer IDs are sufficient. No real personal data is needed.

## 2. Fulfillment, COD, refunds, and RTO

For this demonstration, recognize merchandise sales on delivery. Show placed-order value separately, labelled as such. Payment collection and settlement are separate states from revenue recognition.

- Prepaid undelivered orders are not delivered sales merely because payment was captured.
- Delivered COD orders contribute revenue; unremitted COD is separately visible as unsettled cash.
- Failed COD/RTO orders produce no delivered merchandise revenue and incur applicable forward/reverse logistics and fees.
- RTO is distinct from a post-delivery customer return.
- A refund does not prove inventory recovery. A returned item does not prove full recoverable value.
- Demonstration net product cost is delivered COGS less recognized recoverable returned inventory value, plus explicit failed-delivery damage/loss costs. Intact RTO inventory is not charged again as sold COGS.
- Cancellation before shipment has no delivered revenue; record any actual fees incurred.

These conventions define management reporting for the demo, not a statutory accounting system.

## 3. Contribution and ratios

```text
Net sales excluding tax
  = delivered merchandise value before discounts
  - allocated discounts
  - refunded recognized merchandise revenue
  + retained customer shipping revenue excluding tax

Contribution before ads
  = net sales excluding tax
  - net product cost
  - outbound shipping and fulfillment expense
  - payment/COD collection/transaction fees
  - reverse logistics and return processing expense
  - other defined variable costs

Contribution after ads = contribution before ads - ad spend
POAS = contribution before ads / ad spend
Connected-platform MER = net store sales excluding tax / (Meta spend + Google spend)
```

Do not call contribution accounting net profit. Zero-spend ratios are undefined. Keep negative contribution visible.

Example: net sales INR 4,000; net product cost INR 2,200; other variable costs INR 500; ad spend INR 1,000. Contribution before ads = INR 1,300; after ads = INR 300; POAS = 1.3; MER = 4.0 when these are the complete store totals for the period.

## 4. Return-adjusted estimates

Realized results include known events. Expected results additionally deduct a reserve for future incremental contribution loss from still-exposed orders. Reserve estimates incorporate recoverable inventory and additional return costs, not only gross refund value.

When a return becomes actual, remove that order's reserve and record the actual events. Never retain both the full reserve and full actual loss. Report sample size, cohort maturity, and reserve assumptions. Synthetic reserve calibration is not evidence of real accuracy.

## 5. Attribution and campaign profit

Default first-party demo model: last identifiable paid click within seven days before order placement, with no view-through attribution. Model/window are versioned and visible.

- Keep platform-reported attribution separate from first-party attribution.
- Keep unattributed orders in their own bucket.
- Under this model, an order belongs to at most one campaign; allocated contribution must reconcile to total eligible order contribution.
- First-party campaign contribution follows actual order-line economics, not a platform-reported gross revenue multiplier.
- Show attributed campaign contribution as attribution-based, not proven incremental profit.
- A refund is assigned back to the original acquisition cohort while retaining its actual refund date.
- Campaign IDs, not names, establish identity. Ad/product mappings have provenance, confidence, and validity dates.

## 6. Inventory rules

Sellable inventory uses the source's available quantity for the eligible warehouse, minus only an explicitly separate merchant reserve. Never subtract already-excluded commitments twice.

```text
Daily velocity = eligible units sold / observed in-stock exposure days
Days of cover = sellable units / estimated daily demand
Weighted size availability = available key-variant demand weight / total key-variant demand weight
```

Default baseline: trailing 28 days, using in-stock exposure where known. New/sparse products display insufficient evidence. Zero stock with observed demand is an immediate stockout; zero observed demand does not prove infinite safe cover.

Default demonstration policies:

| Policy | Default |
|---|---|
| Lead time | 14 days, marked merchant-configured assumption |
| Safety buffer | 3 days |
| Warning | Cover below lead time + buffer |
| Throttle proposal | Cover below 5 days with no replenishment before projected stockout |
| Pause proposal | No sellable stock, or unavailable key-variant weight at least 60% |
| Recovery proposal | Positive stock, at least 7 days cover, and unavailable key-variant weight below 40% |
| Execution freshness | Inventory snapshot no older than 15 minutes and live simulated state rechecked |

Availability weights use in-stock sales shares; configurable merchant weights are the fallback. Every status/budget change still requires approval. Recovery is proposed only for an AdVergent-paused object when other blocking conditions are cleared.

A mixed-product campaign cannot be paused solely because one product is unavailable. Require supported narrow control or present an advisory recommendation.

## 7. Predictive and diagnostic baselines

- Clearance: compare price/spend scenarios against a no-action baseline; label stock-age and holding-cost assumptions. Enforce nonnegative expected contribution by default and available-stock limits. No campaign/discount publishing.
- Breakout: rank view growth, add-to-cart rate, comparable ad CTR, margin, and inventory readiness. Initial evidence floor: 100 observed product views and 20 add-to-cart events in the evaluated window; these are demo defaults, not a claim of statistical significance.
- Cohorts: first purchase means earliest delivered purchase in available history. Mark incomplete history. Allocate multi-product first purchases fractionally by net merchandise value, with weights summing to one. Compare mature 60/90-day contribution windows separately from immature cohorts.
- Budget optimization: maximize estimated contribution after ads under a fixed INR daily-budget total, inventory eligibility, and a default 10% per-resource change bound. Abstain when a response curve lacks suitable data. Re-evaluate recommendations after each action.
- Creative fatigue: compare like-for-like seven-day windows; flag possible fatigue only after configured impression/click evidence thresholds. Avoid causal claims.
- Destination/price checks: deterministic fixtures for healthy pages, repeated 404s, redirects, bot blocks, archived products, variant prices, and expired offers. Real crawling is deferred.

## 8. Action contract

State: proposed -> approved -> revalidating -> executing -> succeeded / partially_succeeded / failed / unknown. Also support rejected and expired.

- Approval expires after 30 minutes by default and binds exact object IDs, amounts, currencies, status changes, and evidence version.
- Re-read simulated platform state before writing. Intervening changes invalidate the proposal rather than silently changing its terms.
- Lock affected resources and deduplicate approval/execution attempts.
- Transfer equal INR amounts, not equal percentages. Shared budget impact must be shown.
- Reduce donor, verify, then increase recipient. A timeout requires read-back before retry.
- Never blindly compensate over a later merchant edit. Record partial results and require approval for a new recovery mutation unless it was explicitly included in the original approved plan.
- A proposed rollback cannot recover advertising already spent.
- Verify writes by reading adapter state. Record actor, timestamps, request IDs, before/after values, errors, and evidence version.
- A kill switch blocks new mutations; dependent actions stop when data is stale or unavailable.

### October 31 Phase 12 implementation clarification

The separately authorized [budget contract](../phase-12-budget.md) implements conservative read-only fixed-total allocation under at most 10% per-budget changes. Complete reporting and mature 60-day order outcomes support descriptive rational slope envelopes only; sparse/unknown evidence abstains, every mapped product must have clear fresh inventory, and shared members remain whole. Fixed-budget after-ad delta is a sensitivity scenario assuming full budget delivery, not causal response, incremental profit or calibrated LTV. Blocked budgets freeze without endorsing their unsafe baseline. Cohort 60/90-day maturity, incomplete history and missing costs remain separate context. Every future advertising mutation still requires Phase 8's own exact explicit approval/revalidation; the optimizer creates no action or consent.

## 9. Synthetic dataset contract

Proposed deterministic fixture: 180 days of history, approximately 30 apparel products, 180 variants, 1,000 customers, and 3,000 orders across Meta and Google campaign fixtures. Adjust counts for measured local capacity without removing acceptance scenarios.

Include normal sales, promotions, stockouts, partial returns, COD/RTO, repeat buyers, missing costs, ambiguous mappings, late updates, low-volume products, and unsuccessful action attempts. Keep designated hand-calculated golden cases separate from random generation. Persist random seed, dataset version, and scenario clock; scenario time must not bypass actual approval expiry.

## October 30 Phase 5 implementation clarification

The [finance contract](../phase-5-finance.md) implements sections 1–5 for synthetic local inputs. It documents exact largest-remainder order allocation, targeted historical corrections, explicit recovery valuations/effective dates, delivered revenue versus tax-inclusive settled/unsettled cash, partial-unit reserve replacement and unknown-cost propagation. Reserve defaults (30 days, 10% return probability, 80% recovery and INR 50 extra return fee) are synthetic uncalibrated assumptions. Transaction/acquisition dates remain separate; POAS and MER use decimal ratios with null for zero spend. Snapshot MER is scoped to the supplied bounded ad reports with differing input cutoffs, not verified continuous merchant-period coverage. Full-store contribution remains unknown when required costs are missing, with covered-only subtotals labelled. No later inventory/action thresholds become implemented by this clarification.


## October 30 Phase 6 implementation clarification

The [inventory contract](../phase-6-inventory.md) implements section 6 over explicit synthetic warehouse counters and real Exasol features, with pinned Phase 5 finance context. Unknown leads remain null instead of silently receiving 14 days. A ten-unit/seven-in-stock-day evidence floor, complete key-size rates (or complete explicit merchant fallback weights), ordered sufficient confirmed receipts and affected-scope 900-second freshness are visible implementation defaults. Commitments are never subtracted twice. Zero observed demand yields unknown cover. Recovery additionally requires prior simulated AdVergent pause evidence, exact capability/mapping validity and cleared blockers. Mixed products cannot broaden a one-product pause. These are advisory results; Phase 8 approvals/execution remain unimplemented. Historical contribution/daily scenario are not incremental profit or calibrated forecasts.


## October 30 Phase 7 consumer clarification

Section 7 diagnostics is implemented with fresh spaced repeated-404 evidence, exact selected-variant/catalog/page/ad integer-paise comparisons, expiry/redirect/bot/archive distinctions, adjacent seven-day segmentation-matched windows and explicit 1,000-impression/20-click floors per window with a 30% relative CTR decline. These are configurable uncalibrated implementation defaults. Possible fatigue is descriptive only; fixed catalog-size/color review templates abstain on mapping/inventory/destination blockers. Every review remains advisory and approval-required. See the [diagnostics contract](../phase-7-diagnostics.md).


## October 30 Phase 8 consumer clarification

The separately authorized [approved execution module](../phase-8-approved-execution.md) consumes exact reviewed whole-resource/member scope, capabilities and current coherent analytical evidence. Every simulated pause, throttle, transfer, resume or inverse recovery requires its own durable exact explicit approval and actual-clock revalidation. Imported prior-pause evidence is never an execution ledger or approval. Recommendations remain advisory; no live API capability or mutation is established. Phase 8 gate evidence is recorded separately in its handoff. Earlier module boundaries remain historical.

## October 31 Phase 9 clearance clarification

Section 7 clearance is implemented as a read-only what-if: pinned real Exasol stock/catalog/demand, deterministic assumed-age/excess ranking, explicit full-price no-action baseline and configurable markdown/bundle/additional-spend alternatives. Missing required costs preserve unknown contribution, and exact per-component stock/contribution/margin constraints apply. All future sales/age/holding/variable/return-loss inputs are labelled uncalibrated assumptions; there is no fitted response or causal/incremental-profit claim. No advertising/discount/bundle publishing, approval grant or execution connection exists. Exact equations/defaults: [clearance contract](../phase-9-clearance.md); dated gate evidence: [Phase 9 handoff](../handoffs/phase-9.md).

## October 31 Phase 11 cohort clarification

The separately authorized [cohort contract](../phase-11-cohorts.md) implements first observed delivery and exact rational historical net-merchandise weights. Rolling half-open 60/90-day realized before-ad event windows remain separate by customer maturity, even within a single acquisition month. Acquisition-order pre-delivery expenses count once; refund/recovery events keep actual dates, and later refunds cannot change earlier windows or weights. Missing costs retain unknown totals with separately labelled coverage/subtotals. Every assignment retains incomplete-history status; retrospective source snapshots do not establish historical knowledge, calibrated LTV or incremental profit. Cash, reserves, ad spend and funnel events never become contribution. Only Phase 11 is authorized; no later module or action authority follows.

## October 31 Phase 10 consumer clarification

The [breakout contract](../phase-10-breakout.md) implements the 100-view/20-cart demo floor with additional labelled comparison, ad, coverage, finance and inventory gates. Deduplicated funnel purchase references add zero revenue; unknown margin and sparse/stale evidence remain unranked. Later time-window follow-up is independent of the score, not a backtest or validated prediction. No budget forecast or action authority follows.
