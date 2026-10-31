# Phase plan and acceptance gates

October 31, 2026 IST: **Phase 14 separately authorized; in progress, gate pending**. [Runbook and gate](phase-14-demo.md), [complete included acceptance matrix](phase-14-evidence.md), [active handoff](handoffs/phase-14.md). A25 uses preserving run isolation after retained partial actions under the no-destructive-reset requirement; A26 requires actual SQL rollback and prior-version browser evidence. Existing deployment recovery, sequential non-mutating regression, rehearsal and complete known-gap reporting remain mandatory. Earlier unstarted statements below are historical. No change to roadmap numbers, budget, approval or business rules.

October 31, 2026 IST: **Phase 13 synthetic local unified-decisions gate complete** in its separately requested chat. The [contract](phase-13-decisions.md) covers one coherent decision per resource, inventory precedence, fixed-total conflict suppression, stale-proposal invalidation, grounded explanations and durable outcome observations. Evidence: **249 isolated passes / 22 skips**, **269 broad real-store passes**, then **one focused real-store pass / one deselected**; final healthy/actual-outage browsers **15 passed / 12 mode skips each**. Commands are separate; initial finance-browser failure and focused/final passing reruns are documented in the [handoff](handoffs/phase-13.md). All defaults, private/TLS/volumes/action history preserved; no advertising mutations or later module. **Phase 14 remains unstarted and needs another requested chat**. Earlier Phase 12-only closeout is historical; the full overdue milestone remains incomplete.

Current closeout, **October 31, 2026 IST: Phase 12 only; synthetic local A21 gate complete**. Phases 0–11 retain their documented gates. Phases 13–14 remain unstarted and need separate requested chats. The October 30, 23:59 IST deadline has passed; the full milestone remains incomplete. [Budget contract](phase-12-budget.md), [Phase 12 handoff](handoffs/phase-12.md). Earlier unstarted statements below are historical.

A21 verifies exact fixed existing INR total, at most 10% change bounds, attractive-stockout precedence, whole shared scope, rational conservative response sensitivity and unsupported-data abstention. Real Exasol default reports remain sparse; no supported curve or calibrated LTV is fabricated. Cohort context retains separate mature/immature/missing windows and incomplete history. Budget queries bind six pins and read-only durable state/clock evidence, with no new action authority or later-module implementation.

## Roadmap identity



Preserve the original phase numbers across chats. The October 30 synthetic milestone compresses their demonstration scope; it does not make live/production phases complete. Confirm explicitly if the user wants to regroup phases. Targets are plans, not completed results.



| Phase | Requirements and end-to-end outcome | Acceptance gate | Dependencies / status |

|---|---|---|---|

| 0 â€” Product and feasibility | Scope, metrics, architecture, capability matrix, acceptance cases, hosting decision | Requirements and supported conditional deployment/fallback documented; research/prerequisite evidence recorded; runtime verification retained as Phase 1 gate | Complete at planning level; not deployed or runtime-tested |

| 1 â€” Foundation | Authenticated UI -> API -> real Exasol metric; operational state and repeatable setup | Golden metric matches; repeat load stable; unauthorized access denied; database failure shown | Complete locally: real PostgreSQL/Exasol integration and healthy/outage browser checks passed October 27; cloud remains unverified |

| 2 â€” Commerce mirror | Fixture-based Shopify-shaped ingestion, catalog, customers, orders/lines, refunds, inventory, reconciliation | Duplicate/out-of-order/missed changes reconcile; import resumes; freshness visible | Complete locally October 30: real-store resume/reconciliation/replay/rollback, 3,000-order load and healthy/actual-outage browser checks. Live Shopify deferred; see Phase 2 handoff |

| 3 â€” Ad reporting | Stateful Meta/Google fixture adapters and normalized hierarchy/spend | Spend/currency/timezone fixtures reconcile; delayed reports replace values; capabilities visible | Phases 1â€“2 reused; complete locally October 30: real-store corrected/zero/delayed reports, replay/resume/rollback, authenticated reporting/capabilities, source evidence and healthy/actual-outage browser checks. Live auth/API fidelity deferred; see Phase 3 handoff |

| 4 â€” Mapping/attribution | Product/ad mappings, confidence, overrides, first-party attribution | Ambiguous mappings abstain; multi-product relationships correct; allocation reconciles | Complete locally October 30: reviewed mappings, ambiguity abstention, pinned unique first-party assignments, exact real-store allocation and authenticated healthy/outage browser gate; see Phase 4 handoff |

| 5 â€” Finance | Line economics, contribution, POAS/MER, refunds, COD/RTO, cost coverage | A01â€“A08 financial fixtures; reserve replacement; zero-spend undefined; no silent missing costs | Complete locally October 30: A01â€“A08 finance, actual line/campaign/date reconciliation, correction/cost coverage, reserve replacement, zero spend, real-store failure/replay and authenticated healthy/actual-outage browser gate. See Phase 5 handoff |

| 6 â€” Inventory | Demand/cover, lead times, weighted size-run risk and evidence | A09â€“A11 plus freshness/recovery rules; no unsupported broad pause | Complete locally October 30: A09â€“A11, exact stock/exposure/size/receipt/freshness/recovery, pinned finance, actual SQL failure/replay and authenticated healthy/actual-outage browser gate; see Phase 6 handoff |

| 7 â€” Diagnostics | Fixture destination/price checks and fatigue/creative suggestions | A22â€“A24; transient errors distinct; variants respected; copy grounded | Phases 2â€“6; complete locally October 30: A22â€“A24, comparable-window/evidence-floor fatigue, grounded escaped suggestions, exact scope/inventory gating, SQL failure/replay and authenticated healthy/actual-outage browser checks; see Phase 7 handoff |

| 8 â€” Approved execution | Durable approvals, exact budgets, simulator writes, locks, recovery, audit | A12â€“A17; duplicate/expired approval safe; partial/unknown state explicit; kill switch works | Foundation auth plus coherent Phases 2-7 and exact operator proposal; complete locally October 30: A12-A17 approvals/rejection, proof/expiry, locks/idempotency, simulator read-back/partial/unknown/recovery, post-read-back edit protection and kill switch; see Phase 8 handoff |

| 9 — Clearance | Deadstock ranking, configurable markdown/bundle/spend scenarios | A18; stock/cost/contribution/margin limits and no-action baseline; no publishing | Complete locally October 31: real pinned Exasol ranking/comparisons, exact loss/floors/stock/coverage, fresh synthetic stock and pin changes, authenticated healthy/actual-outage gate; see Phase 9 handoff |

| 10 — Breakout | Synthetic funnel signals, coverage, ranking, inventory readiness | A19; deduplicated events; no double revenue; minimum evidence and time-based evaluation | Phases 2–3, 5–6 with inherited mapping pins; complete locally October 31: actual Exasol deduplication/windows, exact floors, nullable historical margin/clear inventory, holdout independence, SQL rollback/replay, changed pins and authenticated healthy/actual-outage checks. See [Phase 10 handoff](handoffs/phase-10.md) |

| 11 — Cohorts | First delivered purchase, exact fractional multi-product assignment and mature 60/90-day contribution | A20; repeat buyers, partial cohorts, missing costs/incomplete history; no future leakage | Phases 2, 4–5; complete locally October 31: verified Exasol joins/dated contribution, exact fractions/paise, mature/partial windows, missing-cost/history coverage, cutoff/pin/corruption checks and authenticated healthy/actual-outage gate; see [contract](phase-11-cohorts.md) and [handoff](handoffs/phase-11.md) |

| 12 â€” Budget optimization | Conservative response baselines and constrained INR allocation | A21; fixed budget/change limits; inventory precedence; abstention and uncertainty | Phases 5â€“6, 8; Phase 11 for separate maturity/history context; complete locally October 31: A21 policy, real fresh stockout/exact mapping, fixed-total SQL reconciliation, auth/terms/pin/state/clock/corruption checks and healthy/actual-outage browsers; see [contract](phase-12-budget.md) and [handoff](handoffs/phase-12.md) |

| 13 â€” Unified decisions | Conflict resolution and recommendation outcome tracking | One coherent decision/resource; stale proposals invalidated; evidence-grounded explanations; durable observations with unknown financial effect | Phase 8 plus delivered modules; complete at synthetic local gate October 31: exact owner/shared scope, protection/fixed-total conflict rules, pin/state/ledger/clock invalidation, persisted observations and explicit exact action-link policy; real-store/browser/preservation checks pass; [contract](phase-13-decisions.md), [handoff](handoffs/phase-13.md) |

| 14 — Demo hardening | Existing local deployment, preserving run isolation/recovery, regression, rehearsal | A25–A26 and all included cases; complete evidence matrix; known gaps visible | Separately authorized October 31; in progress, gate pending; no advertising mutations/destructive reset; live pilot deferred |



## Verification catalog and phase closeout



Detailed A01â€“A26 scenarios, source/capability matrix, and deployment risks: [Phase 0 verification plan](phase-0/verification-plan.md).



For each phase, carry forward requirements, demo steps, critical failure cases, exact commands/results, outstanding gaps, and next dependencies into its handoff. Extend acceptance cases when implementation exposes a material gap. Do not mark fixture/simulator evidence as sandbox or live verification.



## Deadline tracking



Deadline remains October 30, 2026, 23:59 IST. Phase 0 closed October 27, one day after its original target. The [deployment decision](phase-0/deployment-decision.md) records compressed remaining targets and stop conditions. Phase 1 must establish runtime feasibility first; its chat must re-estimate actual effort. The four-pillar demo remains the target, not a guarantee; do not silently reduce scope or declare original production phases complete.



October 30 correction after Phase 3: local Phases 1â€“3 gates are met, but Phases 4â€“14 remain unstarted. The earlier October 28â€“29 targets were missed; there is no evidence that the full four-pillar scope is complete or will fit the remaining hours. The latest chat delivers only Phase 3. No roadmap scope or phase boundary is waived; start Phase 4 only in its own user-requested chat.



## October 30 Phase 4 closeout correction



The user authorized Phase 4 in its own chat. Mapping/attribution now meets its synthetic local gate: reviewed relationship sets with provenance/confidence/validity/overrides, native-hint abstention, versioned first-party assignment, separate overlapping platform claims, retained unattributed orders, purchased-line/product/refund reconciliation and prior-publication preservation. This prepares A07/A11/A16/A26; it does not complete financial A07 contribution recognition or action safety. Phases 5â€“14 remain unstarted. The deadline and missed earlier targets remain unchanged; the full four-pillar milestone is incomplete. No automatic phase advancement. See [Phase 4 handoff](handoffs/phase-4.md).


## October 30 Phase 5 closeout correction

The user authorized only Phase 5 in this separate chat. Finance now meets its synthetic local gate: actual Exasol line economics, unknown-cost coverage, explicit historical corrections, delivery/cash separation, refunds/COD/RTO, remaining-unit reserve replacement, POAS/connected snapshot MER and unique pinned first-party allocation including unattributed orders. A01â€“A08, exact reconciliation, SQL failure/replay and actual analytics outage have executed evidence. Final backend suite: 61 passed with real integration; isolated: 56 passed/five skips. Healthy and actual-outage browser modes: eight passed/five mode-specific skips each. Source cutoffs, bounded report coverage and uncalibrated reserves remain explicit limitations; no incremental/live/statutory claim follows. Only Phase 5 closes here. Phases 6â€“14 remain unstarted, the full four-pillar milestone is incomplete, and the deadline/missed earlier targets remain unchanged. See [Phase 5 handoff](handoffs/phase-5.md).


## October 30 Phase 6 closeout correction

The user authorized only Phase 6 in this chat. Inventory meets its synthetic local gate: actual Exasol stock/demand/exposure/cover/weighted-size calculations, explicit sparse/zero/unknown evidence, lead assumptions, sufficient time-aware receipts, wall-clock freshness, restricted system-pause recovery and exact valid mapping/capability constraints. Product advice cannot broaden mixed-resource pause; every recommendation remains approval-required/mutation-disabled. Nullable pinned finance provides historical context and an uncalibrated daily scenario, never incremental profit. Backend: 87 real-store-enabled passes; isolated: 81 passes/six skips. Authenticated healthy and actual-outage browser modes: nine passes/six mode-specific skips each, covering all fifteen cases (two inherited rendering substitutes). Existing stores, pins, volumes and six default publications are restored, with historical source age unchanged. Only Phase 6 closes; Phases 7â€“14 remain unstarted. The full four-pillar milestone, deadline and missed earlier targets remain unchanged. See [Phase 6 handoff](handoffs/phase-6.md), including its ready-to-use Phase 7 starter prompt.


## October 30 Phase 7 closeout correction

The user authorized only Phase 7 in this chat. Diagnostics meets A22-A24 and its synthetic local gate: spaced fresh repeated-404 evidence distinct from transient/bot/redirect uncertainty, archive/expiry/selected-variant prices, actual differently priced variants of the same product, comparable closed-window/floor fatigue, escaped malicious evidence, fixed catalog-grounded review suggestions and exact reviewed scope/capability/inventory constraints. Reviews remain advisory/approval-required/mutation-disabled. Backend: 114 real-store passes/no skips; isolated: 106 passes/eight integration skips. Authenticated healthy and actual-stopped-Exasol modes each pass ten/seven mode-specific skips, covering all seventeen cases; two inherited cases remain rendering substitutes. All seven defaults and healthy stores were restored, historical observations remain stale, and direct queries confirm matching input pins. No live crawling, causal/model claim, advertising execution, paid provisioning or later module follows. Only Phase 7 closes; Phases 8-14 and the full milestone remain incomplete. Deadline/missed earlier targets remain unchanged. See [Phase 7 handoff](handoffs/phase-7.md), ending with the ready-to-use Phase 8 prompt. Do not advance automatically.


## October 30 Phase 8 authorization

Only Phase 8 is authorized in this chat. A12-A17 synthetic local gate is now met; exact executed evidence is recorded in the Phase 8 handoff. Exact scope/defaults: [execution contract](phase-8-approved-execution.md). Phase 9 requires a new user-requested chat.


## October 30 Phase 8 closeout correction

Only Phase 8 closes: durable exact explicit approvals/withdrawal, actual-clock proof/expiry, coherent real analytics, exact resource/member state locks, INR transfers, partial/unknown read-back, approved recovery and kill switch. Backend evidence is 130 isolated passes/ten real-store skips; 138-pass full real-store regression plus final focused execution/clock/donor-edit checks. Authenticated healthy and actual-outage browser gates cover all twenty cases, with two inherited rendering substitutes. All seven defaults and healthy stores are restored; historical freshness and isolated action history remain preserved. See [Phase 8 handoff](handoffs/phase-8.md). Phases 9-14 and the full milestone remain incomplete; Phase 9 needs a new user-requested chat. No live action, provisioning, paid API or automatic advancement.

## October 31 Phase 10 closeout correction

Only Phase 10 closes at its synthetic local A19 gate. Default historical source stays stale and sparse p0 remains unranked; explicit fresh complete-cost p3 can rank in controlled real-store checks. No funnel event adds revenue, no score becomes a confidence probability or budget forecast, and separate later evaluation never enters the score. Existing coherent commerce/ads/attribution/finance/inventory pins and content-addressed raw analytical source replace any need for a new operational publication pointer. No dependency scope waiver or action authority follows. Evidence: 172 isolated passes/fifteen skips; 182 broad non-mutating real-store passes plus final focused commands; healthy and actual-outage browsers twelve/nine mode skips each. All seven defaults, healthy stores, private/TLS/launcher/volumes and 60 retained exact approved receipts restored/preserved. Phases 11–14 remain unstarted, the deadline has passed and the full milestone remains incomplete. Phase 11 requires a new requested chat; do not advance automatically.
