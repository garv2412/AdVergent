# AdVergent product specification

October 31 Phase 14 authorization: demo hardening is in progress, with gate pending. [Demo contract/runbook](phase-14-demo.md) and [A01–A26 evidence matrix](phase-14-evidence.md) define preserving run isolation after partial actions, actual failed-refresh preservation, deployment restart, regression and rehearsal. A25 uses new isolated synthetic resource namespaces and retained history under the user's no-destructive-reset requirement. The UI persistently labels stale evidence, missing costs, abstention and separate explicit approval. Business semantics and action authority are unchanged. Earlier Phase 14-unstarted statements are historical; final executed status belongs in the [handoff](handoffs/phase-14.md).

October 31 correction: **Phase 13 is complete at its synthetic local gate; Phase 14 remains unstarted**. The [unified decisions contract](phase-13-decisions.md) governs one exact resource decision, inventory precedence, whole fixed-total allocation suppression, stale-proposal invalidation and durable recommendation observations. Explanations retain delivered module evidence and abstention. Clearance/breakout are context; cohort maturity, missing costs and incomplete history remain separate. An explicit exact action link reports recorded status/read-back only; without a link outcome is not observed, and financial benefit always remains unknown. Recording never grants action authority. Verification and limits: [Phase 13 handoff](handoffs/phase-13.md).

Last updated: 2026-10-31 (IST). Status: Phases 1–13 verified at their documented synthetic local gates with real PostgreSQL/Exasol. Phase 13 evidence is recorded in its handoff. Phase 14 remains proposed and requires another requested chat. No full-milestone, live-effectiveness or production-readiness claim follows.

## Accepted scope

The authoritative Phase 0 product baseline is [phase-0/README.md](phase-0/README.md), sections 1–5. It records the agreed single-merchant apparel scenario, INR/India reporting, October 30 at 23:59 IST deadline, synthetic end-to-end demonstration across four pillars, real Exasol calculations, and approval-required simulated advertising changes.

The prototype is intended to evolve into SaaS. Live integrations, production hardening, and validation on real merchant history follow the synthetic milestone. INR 0 infrastructure/API charges are a hard constraint; no paid upgrade is authorized. User-supplied AWS console text reports USD 139.73 and free access until February 3, 2027 or credit depletion, consistent with the Free plan. At Phase 1 start the user reconfirmed Free-plan status and explicitly accepted local whole-application fallback. A new balance was not supplied. AWS eligibility/quota/resource-cost checks remain unverified; no cloud resources were provisioned. Local foundation runtime is verified; see the [Phase 1 handoff](handoffs/phase-1.md).

## Foundation slice

The implemented engineering defaults are React/TypeScript/Vite, FastAPI, PostgreSQL operational state, and a PyExasol analytics adapter. The single operator signs in with a configured password; the API uses expiring, hashed server-side session records and same-origin POST protection. The UI labels synthetic data, real Exasol analytics and simulated actions persistently. The foundation panel itself has no mutation controls; approved simulations are a separate Phase 8 module.

The first metric uses the hand-calculated two-line delivered-sales example from the metric contract: INR 4,000 sales, INR 2,200 product costs, INR 500 variable costs and INR 1,000 spend; expected contribution is INR 1,300 before ads and INR 300 after ads. This is foundation arithmetic, not the full financial module, attribution, refund, COD/RTO or cost-coverage verification. The UI does not serve precomputed fixture outputs as analytics. Database errors suppress current metrics and retain dataset evidence; failed refreshes retain the prior published dataset.

Runtime gates are tracked separately from implementation and isolated contract tests in the [handoff](handoffs/phase-1.md). Setup and security limitations are in the [setup guide](phase-1-setup.md).

## Commerce mirror

Phase 2 adds a deterministic Shopify-shaped fixture adapter for catalog, variants, synthetic customers, orders/lines, refunds and one warehouse's inventory. The proposed 30-product/180-variant/1,000-customer/3,000-order dataset is implemented and loaded into real Exasol. It preserves historical line costs, null missing costs, explicit tax, payment/fulfillment distinctions and refund recovery status. It does not compute the later financial module or connect to Shopify.

Duplicate deliveries, out-of-order revisions and tombstones, missed changes/deletes, checkpoint resume, relationship validation and atomic analytical publication are implemented and tested. Authenticated totals and paginated source records come from Exasol. Freshness uses the source observation and a proposed 900-second threshold; historical fixture data remains stale after re-import. Full contract: [commerce mirror](phase-2-commerce.md); evidence: [Phase 2 handoff](handoffs/phase-2.md). The foundation contribution cards remain a separate two-line golden dataset.

## Ad reporting

Phase 3 adds stateful synthetic Meta/Google reporting adapters, 16 normalized hierarchy resources, five distinct budgets and revisioned spend. Fixtures cover Meta ad-set/campaign budget ownership, Google Search shared budgets, Shopping-like and separately budgeted PMax-like multi-product resources. Native product references are unverified source hints, without commerce mappings or attribution. Capabilities, budget ownership/members, unsupported product controls and mutation-disabled state are visible.

All money is exact INR paise. Source timezone/day is retained while UTC half-hour intervals convert explicitly to Asia/Kolkata reporting days. Duplicate reports/replays are stable; delayed intervals add once and corrections replace earlier amounts, including zero. Initial/corrected spend reconciles to INR 2,900.21/2,100.22 in real Exasol. Authenticated reporting exposes query/source/dataset evidence, stale source age, failed imports and analytics unavailability. PostgreSQL owns durable adapter cursors/revision state and publication; Exasol owns analytical facts, hierarchy joins and spend aggregation. Full semantics, defaults and limitations: [ad-reporting contract](phase-3-ad-reporting.md); verification: [Phase 3 handoff](handoffs/phase-3.md).

Phase 3 introduced no live authentication/API compatibility claim, advertising mutation or recommendation. Phase 4 mapping/attribution is described below. Every future advertising change still requires explicit approval. Foundation contribution cards remain separate from both full commerce and ad-reporting publications; full commerce finance is described in Phase 5 below.

## Phase 4 mapping and attribution

Implemented reviewed product sets with provenance, confidence, half-open validity, explicit overrides and ambiguity abstention. Native product references remain unverified hints; multi-product sets never imply narrow controls. Versioned first-party last-paid-click attribution retains every placed order once, keeps synthetic platform claims separate, and allocates purchased lines through real Exasol joins. Refund links retain original assignment and actual event date. Finance is added separately in Phase 5 below.

The seven-day inclusive window, 90% candidate confidence floor, exact-resource scope and timestamp-tie abstention are labelled implementation defaults. PostgreSQL owns immutable configuration/override snapshots and attempts; published analytics live in Exasol. Authenticated inspection exposes input versions, model, stale source evidence, changed upstream dependencies, failure preservation and unavailability. Detailed semantics, trusted CLI configuration workflow and limitations: [Phase 4 contract](phase-4-mapping-attribution.md); evidence: [Phase 4 handoff](handoffs/phase-4.md).

## Phase 5 finance

Implemented synthetic delivery-based line economics, contribution before/after ads, POAS and connected-platform snapshot MER, refunds/recovery, COD/RTO, cost coverage, return reserves and separate cash settlement. Missing costs leave full contribution unknown with an explicitly covered subtotal. Historical corrections preserve original line provenance and prior versions. Partial actual outcomes replace the affected units' reserve; remaining units retain exposure. Negative contribution remains visible and zero-spend ratios are undefined.

Finance pins the existing unique first-party assignments and commerce/ad inputs; Exasol reconciles every actual line and unattributed order. Platform claims and the separate foundation cards never enter full commerce totals. Separate transaction/acquisition-day views retain refund/recovery/cash event dates. Reserve rates/window and instantaneous default fixture delivery are labelled implementation defaults, without calibration or merchant-confirmation claims. Differing source cutoffs and bounded synthetic advertising history limit MER's scope to the supplied snapshot. Full contract: [Phase 5 finance](phase-5-finance.md); executed gate: [Phase 5 handoff](handoffs/phase-5.md). Phase 5 closed in its own prior chat. The user authorized Phase 6 separately; its implementation is described below.

## Business rules and assumptions

Read [metric-contract.md](phase-0/metric-contract.md) before implementation. It defines proposed financial recognition, cost allocation, COD/RTO treatment, attribution, inventory policies, cohort assignment, predictive baselines, and action states.

Those detailed defaults were authored as recommendations. The user has not individually confirmed the numerical thresholds, seven-day attribution window, delivery-based revenue convention, dataset size, or approval expiry. Do not describe them as explicitly user-approved. They can guide implementation as labelled defaults; surface material ambiguities before relying on them.

## Acceptance and exclusions

The demo acceptance catalog is [verification-plan.md](phase-0/verification-plan.md), A01–A26. Phases 1–3 verify foundation, commerce and reporting portions of A01/A02/A16/A26 through real stores and browser checks. Phase 2 also verifies safe display of catalog text related to A24; Phase 3 exposes hierarchy/capabilities relevant to future A11 controls, without implementing recommendations/actions. Phase 6 additionally verifies A09–A11 inventory and freshness/recovery restrictions through real stores and authenticated healthy/actual-outage browser checks. Phase 7 additionally verifies A22-A24 through isolated, real-store and authenticated healthy/actual-outage checks; later module acceptance remains pending. The scope exclusions in the baseline remain applicable. Descriptive synthetic outcomes do not validate incremental profit, predictive accuracy, or live API capability.

## Maintenance rule

Update this index and the detailed contract together when a decision changes. Record the reason and affected acceptance cases in the active phase handoff. Keep accepted requirements distinct from implementation defaults.


## Phase 6 inventory

Implemented complete versioned synthetic warehouse stock/demand/exposure observations over the pinned commerce catalog and finance/attribution/reporting inputs. Exasol calculates exact available-minus-reserve stock without subtracting commitments, exposure-based velocity, nullable cover and demand-weighted key-size availability. Lead assumptions, timed/qualified receipts, sparse/zero/missing exposure, stale observations, exact reviewed mapping validity/capabilities and mixed-resource limits remain visible. Product-level advice and supported exact-resource eligibility are distinct; every recommendation requires approval and mutation remains disabled. Recovery requires fresh stock and simulated prior AdVergent pause evidence with all blockers cleared.

The 28-day window, ten-unit/seven-day floor, 14-day lead assumption, three-day buffer, five-day throttle, 60% size-risk pause, seven-day/under-40% recovery and 900-second freshness are implementation defaults, not calibrated merchant settings. Warehouse counters are separate synthetic observations, never extra commerce orders/revenue. Pinned finance supplies nullable historical contribution and an explicitly uncalibrated daily contribution scenario; neither establishes incremental profit. Full semantics: [inventory contract](phase-6-inventory.md); executed gate/status: [Phase 6 handoff](handoffs/phase-6.md). No live integration, advertising mutation or Phase 8 execution module is included. Phase 7 diagnostics is described below.


## Phase 7 diagnostics

Fixture-based destination/variant-price checks and descriptive fatigue review are implemented. Repeated fresh spaced 404s differ from transient uncertainty, redirects, bot blocks, archived products, selected-variant uncertainty and expired offers. Comparable adjacent seven-day windows require explicit impression/click floors. Catalog-grounded fixed review templates use structured size/color facts; untrusted titles/page text remain escaped evidence. Exact reviewed mappings, complete affected inventory constraints and capabilities remain visible. All reviews are advisory, approval-required and mutation-disabled. Real crawling, model calls and advertising writes are excluded.

Detailed implementation defaults, ownership and limitations: [diagnostics contract](phase-7-diagnostics.md). Executed gate evidence: [Phase 7 handoff](handoffs/phase-7.md). These defaults are uncalibrated, not individually merchant-confirmed, and do not demonstrate causal fatigue or ad effectiveness. Phase 8 was separately authorized; its implementation is described below.


## Phase 8 approved execution

Phase 8 meets its synthetic local A12-A17 gate, with exact dated evidence in the Phase 8 handoff. The [approved execution contract](phase-8-approved-execution.md) defines exact proposals, durable approvals, real expiry, revalidation, simulator-only writes, shared-budget scope, equal-paise transfers, read-back, partial/unknown outcomes, separately approved recovery and kill switch. The 30-minute lifetime and global one-merchant execution serialization are labelled defaults. Earlier no-action statements describe the historical module boundaries; the new execution region provides explicit approval controls without live advertising APIs. Phase 9 and later modules remain outside this chat.

The approved digest binds a proof deadline, and the final simulator SQL enforces proof/approval expiry atomically. A recipient locks/rechecks earlier successful targets so later merchant edits cannot silently complete a transfer. Final evidence is isolated policy, real local stores and authenticated healthy/actual-outage flows; it does not establish live platform fidelity or production stability.

## Phase 9 clearance

The separately authorized Phase 9 implements deadstock ranking over pinned real Exasol stock/demand/catalog joins, configurable markdown/bundle/additional-spend alternatives and an explicit full-price no-action baseline. Every component must fit sellable stock; unknown required costs preserve unknown contribution. Exact contribution and margin floors apply. Ranking exposes insufficient demand, individual freshness and assumed stock age; prospective sales, variable/return/holding costs remain labelled uncalibrated assumptions. Current catalog costs never replace historical finance costs. No discount, bundle, campaign or advertising mutation can be published. No execution authority or later module follows, even from a feasible comparison.

Exact defaults, equations and requirements: [clearance contract](phase-9-clearance.md). A18, stock/cost/floor constraints, fresh/changed pins and authenticated healthy/actual-outage checks meet the synthetic local gate; dated evidence and limitations: [Phase 9 handoff](handoffs/phase-9.md). The October 30, 23:59 IST milestone deadline has passed; the full milestone and Phases 10–14 remain incomplete. Phase 10 needs another requested chat.

## Phase 10 breakout

Separately authorized Phase 10 adds synthetic deduplicated funnel events and coverage, comparable closed-window view/cart/CTR signals, nullable historical margin, fresh clear inventory readiness and explicit sparse/stale abstention. A separate later window evaluates descriptive persistence without entering the score. No confidence probability, budget forecast, revenue addition, publishing or advertising mutation is introduced. Exact uncalibrated defaults and storage/interface decisions: [breakout contract](phase-10-breakout.md). A19 passed its synthetic local gate with isolated, real-store and authenticated healthy/actual-outage evidence: [Phase 10 handoff](handoffs/phase-10.md). Phase 11 requires its own requested chat.

## Phase 11 cohorts

The separately requested cohort module assigns customers once to their first observed delivered order, then fractionally to its purchased products by historical net merchandise value. Exact rational customer weights and largest-remainder paise allocations reconcile. First delivery uses finance timestamps; placement, cash capture and later repeat purchases never create a new acquisition. Acquisition campaign uses the pinned unique first-party assignment, including unattributed. Bounded source history is explicitly incomplete; zero-value first orders abstain.

Realized before-ad contribution follows actual delivery, expense, refund and recovery event timestamps. Rolling half-open 60/90-day windows mature only when all pinned source cutoffs cover their end. Mature and immature product/month buckets stay separate, including partially mature months. Missing costs leave full contribution unknown, with event coverage and known customer subtotals separately labelled. Acquisition-order expenses before delivery count once; cash, reserves, advertising spend and funnel observations never become contribution. Later refunds cannot rewrite earlier windows or weights. Retrospective source versions do not establish historical knowledge or predictive validity.

No publishing, action authority, calibrated LTV or incremental-profit claim follows. The [cohort contract](phase-11-cohorts.md) records accepted requirements versus implementation defaults; [Phase 11 handoff](handoffs/phase-11.md) records executed gate evidence. Phase 12 was subsequently authorized in its own chat.

## Phase 12 budget optimization

The separately requested read-only optimizer compares the existing fixed INR daily-budget total under a maximum 10% per-budget change bound (configurable downward). Budgets are distinct whole resources with every shared member visible. Exact paise transfers maximize a conservative descriptive contribution delta only when complete daily reports, mature 60-day attributed order outcomes, complete costs and sufficient repeated spend levels support a slope envelope. No extrapolation, missing-cost substitution or full portfolio forecast is produced. Bundled sparse historical reports abstain.

All mapped products must have clear fresh inventory; stockout, size/cover risk, unknown demand/lead, stale sources, unsupported or ambiguous scope, paused resources, diagnostic blockers and unsuitable response evidence freeze the affected budget. The unchanged unsafe baseline remains visible for comparison, without endorsing continued spending. Source and durable simulator state/revisions, pins, expiry boundaries, kill switch and unknown intents gate the comparison. No source observation initializes or resets action state.

Cohort maturity, missing costs, cutoff and incomplete history remain separate context and never become a response multiplier. An explicitly labelled full-budget-delivery assumption connects spend association to a budget scenario; synthetic association and sensitivity ranges are not calibrated LTV, causal response, confidence bounds, incremental profit or a historical predictive backtest. No publishing, proposal, approval or execution interface is introduced. Requirements versus defaults and exact arithmetic: [budget contract](phase-12-budget.md). Gate evidence belongs in the [Phase 12 handoff](handoffs/phase-12.md). Phase 13 needs another requested chat.
