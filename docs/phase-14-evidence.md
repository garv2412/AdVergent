# Included demo acceptance evidence matrix

Phase 14, October 31, 2026 IST. This matrix distinguishes inherited executed evidence from the current non-mutating regression; final dated counts and actual gate result are in the [Phase 14 handoff](handoffs/phase-14.md). Baseline scenarios: [A01–A26](phase-0/verification-plan.md). Operating and restoration procedure: [demo runbook](phase-14-demo.md). Fixture/simulator evidence never implies live integration, merchant completeness, causal benefit or production readiness.

| Case | Expected behavior and retained inputs | Automated evidence and scope |
|---|---|---|
| A01 | Exact prepaid/zero-return financial arithmetic | `fixtures/finance-v1.json`; `test_finance.py::test_a01_golden_exact_paise_and_ratios`; real finance reconciliation; [Phase 5](handoffs/phase-5.md) |
| A02 | Zero spend leaves ratios undefined | Finance policy golden and real finance correction/reconciliation; `frontend/tests/finance.spec.ts`; no fabricated ratio |
| A03 | Historical effective COGS correction preserves originals | `test_finance.py::test_a03_effective_correction_does_not_rewrite_original_or_other_lines`; real finance/browser corrections |
| A04 | Partial return/recovery/fees and remaining reserves reconcile | `test_finance.py::test_a04_partial_return_recovery_and_reserve_replacement`; real finance/browser reserve checks |
| A05 | RTO/undelivered order has no recognized sale or sold COGS | `test_finance.py::test_a05_undelivered_and_rto_no_sales_or_sold_cogs`; real finance A01–A08 integration |
| A06 | COD contribution remains separate from unsettled cash | `test_finance.py::test_a06_cod_delivered_separate_cash_and_a08_missing_cost`; real finance/API/browser |
| A07 | Competing platform claims never duplicate store revenue | `fixtures/attribution-v1.json`; real attribution and finance unique order/line allocation; attribution/finance browsers |
| A08 | Missing costs leave full contribution unknown | Finance policy and real SQL coverage; browser visible nullable totals, covered subtotal separately labelled |
| A09 | 40 units/10 per day yields four-day cover and throttle review | `fixtures/inventory-v1.json`; inventory policy A09/A10 and real A09–A11 SQL test; [Phase 6](handoffs/phase-6.md) |
| A10 | Unavailable key sizes with 60% weight retain exact variant support | Inventory policy and real stock/weighted-size/exposure queries; inventory browser |
| A11 | No unsupported broad pause for mixed-product resource | Inventory exact-scope policy, actual reviewed mapping/member SQL; unified decision conflict/whole-budget tests |
| A12 | Duplicate explicit approval yields one receipt | Current isolated strict approval tests; historical Phase 8 real `test_real_a12_a17_durable_approved_execution` and browser; receipts retained/hash checked. Mutation suites excluded now |
| A13 | Changed budget/revision invalidates consent | Current isolated execution policy and unified proposal invalidation; historical Phase 8 real revision/edit rejection; six table hashes preserved |
| A14 | Donor success/recipient failure remains exact partial state | Current isolated `test_partial_and_unknown_never_report_success`; historical Phase 8 real recipient failure/kill and approved recovery. A25 requires retained partial plans; no new mutation |
| A15 | Timeout reconciles read-back before retry | Historical Phase 8 real unknown/read-back/idempotency and browser; current isolated unknown-outcome policy and retained audit; no new execution |
| A16 | Analytics/inventory unavailability removes current data and blocks dependent action | Current actual-stopped-Exasol browser suite; real pin/failure/API tests; historical Phase 8 unavailable execution rejection |
| A17 | Only durable approved system pause can support recovery; new approval still needed | Current inventory/execution/unified policy and real inventory provenance; historical Phase 8 approved pause/recovery cycle; no new recovery mutation |
| A18 | Revenue gain with contribution loss fails floors | Default clearance: +40,500 revenue/-45,400 contribution paise; real SQL, independent policy and browser; final inherited audit |
| A19 | Sparse clicks remain unranked with no confidence/forecast claim | `fixtures/breakout-v1.json`; real dedup/window/sparse/fresh rank tests, later holdout independence and browser; final default zero ranks |
| A20 | Mature/immature and missing-cost/history cohorts remain separate | Real exact fractional/event/maturity/cutoff SQL, policy boundary/future-event tests and cohorts browser; final reconciliation audit |
| A21 | Attractive stockout cannot grow; fixed INR total/change bounds | Independent policy attractive slope stockout/exhaustive allocation; separate real fresh stockout and whole-member tests; default five frozen budgets total 1,100,000 paise |
| A22 | Transient uncertainty differs from repeated fresh spaced 404 | `fixtures/diagnostics-v1.json`; diagnostic policy/retry floors, real SQL and browser; [Phase 7](handoffs/phase-7.md) |
| A23 | Same-product distinct variant prices avoid global mismatch | Real dedicated variant-price source test, diagnostic policy and browser selected-variant evidence |
| A24 | Malicious catalog/page text remains escaped inert data | Commerce/diagnostic real source and browser checks; grounded template policy; cannot authorize actions |
| A25 | New run isolated after retained partial action, reproducible semantics and intact history | `backend/advergent/demo.py`; `test_demo_integration.py`; `scripts/rehearse-demo.py`: two fresh disjoint namespaces, equal advice/whole total, no simulator keys initialized, full six-table and inherited observation hashes, defaults restored in `finally` |
| A26 | Midway refresh failure never publishes partial data | Real foundation duplicate-key rollback test plus module SQL-failure cases; `scripts/fail-demo-refresh.py` and `frontend/tests/demo.spec.ts` verify actual SQL rollback, exact prior pointer/metric, authenticated warning and default restore |

Unified-decision requirements supplement the numbered catalog: one exact owner/resource, shared-member scope, inventory precedence, whole fixed-total conflict suppression, pin/state/ledger/clock invalidation, grounded explanations and explicit-only outcome linking. Current `test_decisions.py`, real decision integration/browser and final audit cover these. Historical action links remain policy-only controlled evidence; real observations without links report `not_observed`, financial outcomes unknown.

Two inherited browser cases use route substitutions for rendering and are labelled as such; they are not real-store evidence. Healthy versus outage mode skips are intentional and must be reported separately. Phase 8 mutation suites are deliberately excluded under the current authorization; their dated historical evidence remains in [Phase 8 handoff](handoffs/phase-8.md). No acceptance item is silently relabelled as a new advertising execution.

Known gaps: live source fidelity, calibrated response/LTV, full merchant/cost/history coverage, causal effect, production performance/concurrency/retention, multi-user login hardening and disaster recovery. Graceful restart preserves existing local deployment/mounts; it does not establish hard-kill/power-loss/reboot/new-host recovery. The original October 30 deadline was missed; actual verification dates govern closeout.
