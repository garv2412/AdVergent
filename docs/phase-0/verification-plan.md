# Acceptance, feasibility, and delivery gates



Updated 2026-10-27: Phase 0 planning/research is complete. Runtime execution remains unverified. The [deployment decision](deployment-decision.md) supersedes earlier unknown-account and prerequisite statements below. Historical October 26 targets are retained as plans, not results.



## 1. Evidence levels



1. Contract specified: expected behavior documented.

2. Synthetic verified: executable deterministic scenarios pass.

3. Sandbox verified: actual platform test facilities confirm supported behavior.

4. Live verified: authorized merchant resources confirm integration behavior.



The October 30 milestone targets level 2, with an actual Exasol runtime. It does not imply levels 3 or 4.



## 2. Capability and source matrix



| Capability | Prototype source/action | Later live source | Current status |

|---|---|---|---|

| Catalog, orders, inventory, refunds | Deterministic Shopify-shaped fixtures | Shopify GraphQL Admin API and webhooks | Live access unavailable |

| Customer cohorts | Synthetic customer/order IDs | Permitted order/customer history | Older-order access unverified |

| Views and carts | Synthetic consent/coverage-aware events | Shopify Web Pixel | Live instrumentation unavailable |

| Fees, shipping, COGS | Explicit fixture ledger and settings | Available Shopify/settlement/fulfillment data plus merchant input | Completeness unverified |

| Lead times, receipts, holding cost | Merchant settings/fixtures | Merchant input or later integration | Not assumed to come from Shopify |

| Meta reporting and actions | Stateful simulated adapter | Marketing API | Permissions and object capabilities unverified |

| Google reporting and actions | Stateful simulated adapter | Google Ads API | Developer token and live capabilities unverified |

| Analytics | Real Exasol Personal | Same adapter subject to deployment/license needs | Not installed or connectivity-tested |

| Hosting | AWS Free plan preferred; local Exasol fallback | Conditional no-charge route | User console evidence received; instance eligibility, IAM/quota, and runtime unverified |



Simulated adapters implement application contracts, not assertions of exact external API fidelity. A live adapter must translate and validate actual resource semantics later.



Proposed campaign fixtures: Meta product-linked ads under ad-set-owned and campaign-owned budgets; Google Search and Shopping/PMax-like multi-product cases. Unsupported product-level controls must yield an advisory result. Test a shared Google budget separately from a nonshared PMax budget fixture.



## 3. Required end-to-end acceptance scenarios



| ID | Trigger and path | Expected result |

|---|---|---|

| A01 | Load seed -> Exasol -> API -> dashboard | Golden financial totals match exactly to paise; real analytical query evidence available |

| A02 | Replay same seed/events | Stable counts and totals; no duplicate orders/refunds |

| A03 | Update historical unit cost | Only explicitly effective/affected order periods change |

| A04 | Partial return with recovery and fees | Correct recognized revenue reversal, recovered product value, and costs |

| A05 | COD shipment -> RTO | No delivered sales; forward/reverse costs and applicable losses visible |

| A06 | Delivered COD awaiting remittance | Contribution and unsettled cash remain distinguishable |

| A07 | Both platforms claim one order | Store revenue counted once; platform views remain separate |

| A08 | Missing COGS | Incomplete/estimated status visible; no silent zero-cost profit |

| A09 | 40 units and 10/day demand, 14-day lead time | Four-day cover and approval-required throttle proposal |

| A10 | Key sizes with 60% demand weight unavailable | Weighted size-risk proposal with supporting variants |

| A11 | One product fails in mixed-product campaign | No unsupported whole-campaign pause |

| A12 | Approve pause twice | Exactly one simulated mutation, confirmed by read-back |

| A13 | Budget edited after recommendation | Stale approval rejected; updated proposal required |

| A14 | INR transfer donor succeeds, recipient fails | Partial state and exact actual budgets shown; no false success |

| A15 | Mutation succeeds but response times out | Read-back resolves uncertainty before any retry |

| A16 | Inventory/Exasol becomes unavailable | Stale/unavailable banner; dependent action blocked |

| A17 | Inventory recovers after system pause | Resume proposal only; explicit approval still required |

| A18 | Clearance markdown raises revenue but loses contribution | Scenario exposes loss and fails configured margin floor |

| A19 | Sparse product gets a few clicks | No high-confidence breakout or precise budget forecast |

| A20 | Mature and immature LTV cohorts | Separate reporting; no future-data leakage |

| A21 | Budget optimizer sees attractive stockout product | Inventory constraint wins; total budget and change bounds hold |

| A22 | Fixture URL returns transient error versus repeated 404 | Distinct uncertain versus confirmed issue states |

| A23 | Price differs by variant | Correct variant comparison; no false global mismatch |

| A24 | Malicious product text | Text displayed/escaped as data; cannot authorize actions |

| A25 | Reset demo after partial action | New run cleanly isolated, with reproducible data and state |

| A26 | Refresh fails halfway | Prior complete analytical version remains visible; failed batch not published |



For every scenario retain input fixture, expected outcome, actual result, and automated test or recorded manual evidence. Do not mark cases passed before execution.

Phase 9 A18 implementation and exact golden cases: [clearance contract](../phase-9-clearance.md). Actual default v6 scenario raises revenue by 40,500 paise but reduces expected contribution by 45,400 paise, leaving negative 13,350 scenario contribution and failed contribution/margin floors. Isolated hand-calculated inputs use different price/COGS and distinct expected totals. A18 and the synthetic local clearance gate passed October 31, after isolated/real-store/authenticated healthy/actual-outage checks and restoration; exact separate commands, dated evidence and limitations are in the [Phase 9 handoff](../handoffs/phase-9.md). There is no publishing or advertising mutation in this phase.



## 4. Feasibility register



| Issue | Evidence needed | Decision/fallback |

|---|---|---|

| Zero-cost cloud | Account eligibility; explicit no-overage/no-paid-conversion terms; covered ancillary services | Local Exasol if unresolved; do not provision paid resources |

| Exasol runtime | Supported architecture, memory/storage needs, OS/container support, connectivity, and bulk-load path | Read-only prerequisite inspection before choosing target |

| Hybrid topology | Authenticated API connectivity without public database exposure | Discuss local whole-app fallback only if needed |

| Exasol Personal scope | Single-operator prototype fits documented terms; later SaaS licensing reviewed separately | Do not treat shared credentials as licensing workaround |

| Model usefulness | Synthetic behavior tests now; real holdout/experiment evidence later | Label all predictions appropriately and abstain when unsupported |

| Campaign controls | Actual account capabilities and SDK/API contract validation later | Simulated approval loop only for this deadline |

| Financial completeness | Available real cost sources and merchant conventions later | Actual/estimated/missing flags remain mandatory |



## 5. Proposed deadline sequence



This compresses the original roadmap into demonstration milestones. It does not declare the production phases complete.



| Date (IST) | Target | Exit evidence |

|---|---|---|

| Oct 26 | Finish Phase 0 documents and settle deployment prerequisites | Scope, metrics, fixtures, and runtime plan concrete |

| Oct 27 | Real Exasol vertical slice and synthetic financial dataset | A01-A08 and basic dashboard path |

| Oct 28 | Inventory recommendations and simulated approval execution | A09-A17, including partial failure |

| Oct 29 | Clearance, cohorts, breakout/budget baselines, diagnostics | A18-A24 and coherent recommendation priorities |

| Oct 30 | Deployment, reset/recovery tests, regression, demo rehearsal | A25-A26; all required scenarios reviewed by 23:59 IST |



If a gate slips, surface the shortfall immediately. Do not silently replace real Exasol analytics with static numbers or claim untested features complete.



## 6. AWS account clarification (October 26, superseded October 27)



Initial information was approximately USD 100 with plan unknown. October 27 update: user supplied console text showing USD 139.73, 101 displayed days, free access ending February 3, 2027 or depletion, and an upgrade option. This supports the Free-plan interpretation. It is not an authenticated account inspection. Reconfirm current state before provisioning.



AWS distinguishes a Free account plan, which closes when its duration or credits end, from a Paid account plan, which can charge beyond credits or for ineligible usage. Credits alone do not establish no-charge protection. Avoid upgrades and actions that automatically change the account plan.



Next execution evidence: actual compatible Exasol compute/storage availability, IAM/quota, resource plan, credit consumption estimate, and connection/load tests. The Exasol default instance differs from the Free-plan list. Retain local Exasol fallback if needed. Budget notifications are monitoring, not an enforceable spending cap. See the deployment decision for pinned version/source details.



References checked:

- https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-plans.html

- https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html



## 7. Remaining user information



No further AWS balance/expiry answer is needed now. Runtime preflight belongs to Phase 1 using the recorded deployment decision. Read-only host inspection is complete; Podman and launcher setup are not. No credentials should be pasted into chat. Ask only if account access, deployment restrictions, or a whole-app local fallback require a new user decision.



No additional business preference is currently necessary to write the Phase 0 baseline. The metric defaults can be revised before their implementation if the user prefers different semantics.



## 8. Documentation references



These support feasibility research, not a claim that integrations were tested:



- Exasol Personal: https://docs.exasol.com/db/latest/get_started/exasol_personal.htm

- PyExasol: https://docs.exasol.com/db/latest/connect_exasol/drivers/python/pyexasol.htm

- Shopify inventory: https://shopify.dev/docs/api/admin-graphql/latest/objects/InventoryItem

- Shopify orders/history access: https://shopify.dev/docs/api/admin-graphql/latest/objects/Order

- Shopify webhooks: https://shopify.dev/docs/apps/build/webhooks/verify-deliveries

- Shopify storefront events: https://shopify.dev/docs/api/web-pixels-api/standard-events

- Google developer tokens: https://developers.google.com/google-ads/api/docs/api-policy/developer-token

- Google budgets: https://developers.google.com/google-ads/api/docs/campaigns/budgets/create-budgets

- Meta-owned API collection: https://www.postman.com/meta/facebook-marketing-api/collection/0zr4mes/facebook-marketing-api-mapi

- Render free-tier limitations: https://render.com/docs/free

- Oracle free-resource capacity limitations: https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm



Recheck provider terms when selecting infrastructure. Earlier documentation research does not prove account-specific eligibility or prevent charges by itself.



## October 30 Phase 5 gate extension



A01–A08 are implemented for synthetic financial sources using actual local PostgreSQL/Exasol. The [Phase 5 handoff](../handoffs/phase-5.md) records exact executed evidence and limitations. Additional required cases cover largest-remainder paise reconciliation, partial/full reserve replacement, maturity and missing recovery/expenses, negative RTO contribution, zero connected spend, pinned-input change, SQL rollback, post-commit recovery and actual analytics outage. Isolated assertions, real-store integration and authenticated browser results remain distinct. No sandbox/live integration, statutory accounting or incremental/model accuracy is established. A09–A26 later-module scope remains pending except previously documented foundation/failure portions.





## October 30 Phase 6 inventory gate extension



A09–A11 are implemented for independent synthetic warehouse observations over the pinned commerce catalog and finance/attribution/reporting datasets, using actual local PostgreSQL/Exasol. A09 is the v6 variant with 40 available/ten daily demand/four-day cover and 14-day lead; A10 is the observed 60% unavailable size share; A11 includes an unsafe product alongside a product without pause/throttle conditions, retaining mixed-resource advisory status. [Phase 6 handoff](../handoffs/phase-6.md) records exact final execution and limitations.



Additional required cases cover already-excluded commitments, separate reserve/floor-at-zero, sparse/zero/missing exposure and unknown leads, complete merchant weight fallback and threshold boundaries, receipt quantity/order/timing/gaps/overdue/stale evidence, freshness boundary/replay, prior-system versus merchant/unknown pauses and explicit blockers, mapping validity/confidence/ambiguity, exact/shared budget capability, nullable/negative pinned finance, changed inputs, actual SQL rollback, committed-orphan retry, typed corruption and actual analytics outage. Isolated assertions, actual-store checks and authenticated browser results are separate evidence levels. The two inherited route-substitution browser cases remain rendering-only. Synthetic pause provenance does not establish an action ledger, live integration, incremental profit or calibrated model effectiveness. Phase 7/A22–A24 and Phase 8 action acceptance remain pending.





## October 30 Phase 7 consumer clarification



Phase 7 covers A22–A24 with isolated diagnostic policy, real typed Exasol sources/joins, authenticated healthy checks, genuine failed SQL publication preservation and actual stopped-analytics UI suppression. Evidence levels and exact results belong to the Phase 7 handoff; fixture checks do not establish live reachability, API fidelity or model effectiveness. See the [diagnostics contract](../phase-7-diagnostics.md).



## October 30 Phase 8 consumer clarification

The separately authorized [approved execution module](../phase-8-approved-execution.md) consumes exact reviewed whole-resource/member scope, capabilities and current coherent analytical evidence. Every simulated pause, throttle, transfer, resume or inverse recovery requires its own durable exact explicit approval and actual-clock revalidation. Imported prior-pause evidence is never an execution ledger or approval. Recommendations remain advisory; no live API capability or mutation is established. Phase 8 gate evidence is recorded separately in its handoff. Earlier module boundaries remain historical.

## October 31 Phase 10 A19 extension

A19 additionally requires deduplicated event IDs and order/product callbacks, no added revenue, missing coverage/unknown costs abstention, comparable closed windows, fresh clear inventory, minimum evidence, separate later evaluation without score leakage, actual Exasol typed/source verification and authenticated healthy/actual-outage behavior. Exact executed evidence and limitations: [Phase 10 handoff](../handoffs/phase-10.md). Synthetic persistence is not model effectiveness or causal profit.


## October 31 Phase 12 verification

A21 passes at the synthetic local gate. A controlled response fixture gives the stockout a slope of 100 but freezes its budget; the supported slope-1 donor and slope-3 recipient transfer exact equal paise within 10% bounds, preserving the total. Independent exhaustive small portfolios verify the conservative objective. Fresh real Exasol stockout observations and exact budget-owner mapping independently freeze whole-budget growth. Sparse bundled real reports remain insufficient for a response curve and abstain; no fake fitted response or calibrated LTV is claimed. Shared members, strict fixed totals/change bounds, missing costs, mature outcome windows, daily coverage, uncertainty, pins/state/clock/corruption and authenticated healthy/actual-outage behavior pass. Execution mutation cases are excluded. Separate evidence levels, commands, preservation and limits: [Phase 12 handoff](../handoffs/phase-12.md); rules/defaults: [budget contract](../phase-12-budget.md). No Phase 13 gate or action authority follows.
