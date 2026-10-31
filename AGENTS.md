# AdVergent — project instructions

Current Phase 14: separately authorized October 31, 2026 IST; **in progress, gate pending**. Ordered baseline is project status, [Phase 13 handoff](docs/handoffs/phase-13.md), specification, architecture and Phase 14 plan. Read [demo hardening runbook](docs/phase-14-demo.md) and [included A01–A26 matrix](docs/phase-14-evidence.md). Current work/results: [Phase 14 handoff](docs/handoffs/phase-14.md). Earlier Phase 14-unstarted statements below are historical. Only Phase 14 may close here; there is no Phase 15 in the accepted plan.

## Phase 14 demo commands and boundaries

- A25 is preserving source-run isolation after retained partial actions, never deletion/reset of actions, approvals, receipts, simulator/control state or recommendation observations. `scripts/rehearse-demo.py` prepares two new isolated source namespaces, compares semantic advice/exact fixed total and restores defaults in `finally`; no proposal/approval/execution/simulator initialization method. Fresh timestamps intentionally differ. Keep its actual run manifest private in `.runtime`.
- Before checks, private environment loading then `scripts/verify-demo-state.py --capture` retains six full action/state/control hashes and inherited recommendation-row hashes. Do not recapture after work to hide differences. Final `scripts/verify-demo-state.py` extends all inherited analytical/default/private-file audits. Additional recommendation observations are retained, never cleaned up.
- Isolated `.\.venv\Scripts\python.exe -m pytest -q`; private `RUN_INTEGRATION=1` broad real-store regression `.\.venv\Scripts\python.exe -m pytest -q --ignore=backend/tests/test_execution_integration.py -x`. Browser list is Phase 13's twelve files plus `demo.spec.ts`; exclude `execution.spec.ts`. A26 helper uses an isolated real duplicate-key SQL failure and restores foundation in browser `finally`. Source-changing checks must finish sequentially.
- `scripts/verify-demo-recovery.ps1` operates this host's existing PostgreSQL/Exasol only, proves actual outages, restarts in `finally`, compares persistent mounts, restores `probe` plus all seven defaults and audits preserved history/private/TLS files. Preserve launcher deployment/secrets, `.env`, `.runtime`, trusted certificate and volumes. Never install/rebootstrap/prune/reset/delete or use `compose down -v`.
- All listeners remain loopback. No advertising mutations, action/approval creation, publishing, paid services/provisioning, billing change, destructive resets or history cleanup; INR 0. Report actual dates after the missed October 30 deadline. Historical A12–A17 mutation evidence stays inherited from Phase 8; never claim it was newly executed. Close only when the Phase 14 gate passes and document all known gaps.
- `scripts/restart-demo-api.ps1` restarts only an idle verified loopback AdVergent Uvicorn listener, using existing private environment and hidden process startup. Run after active checks finish; it is not evidence for in-flight request recovery. No public bind or replacement of an unknown process.

Current closeout: **Phase 13 synthetic local unified-decisions gate passed October 31** in its separately requested chat. Ordered baseline was [Phase 12 handoff](docs/handoffs/phase-12.md), Phase 13 plan and [unified decisions contract](docs/phase-13-decisions.md). Final evidence: [Phase 13 handoff](docs/handoffs/phase-13.md). Only Phase 13 closes; Phase 14 remains unstarted and needs another requested chat. Earlier Phase 12-only statements are historical. No advertising mutations, publishing, paid services or action-history cleanup; INR 0. The October 30, 23:59 IST deadline has passed; report actual dates.

## Phase 13 commands and boundaries

- After private environment loading, `worker migrate` adds migration 009 operational recommendation observations only. Authenticated `/api/decisions` composes six coherent pins and delivered verified analytical modules; `/api/decisions/track` records an exact digest/resource observation under existing import/execution locks with atomic proof expiry. `/api/decisions/history` reports explicit exact linked action read-back, never inferred adoption or financial benefit. No action/approval creation or simulator initialization. Retain all observations and action history.
- Inventory protection overrides growth/recovery/creative advice. Meta owners have one resource row; Google budgets retain exact whole members. Any conflicting allocation leg withholds the whole fixed-total comparison. Throttle remains amount-unspecified; recovery needs durable approved pause evidence. Preserve abstention, nullable missing costs, incomplete history and separate cohort maturity. Proposal invalidation is a read-only view; Phase 8 exact explicit approval/revalidation remains mandatory for every future write.
- Isolated: `.\.venv\Scripts\python.exe -m pytest -q`. Private real stores: `RUN_INTEGRATION=1`, `.\.venv\Scripts\python.exe -m pytest -q --ignore=backend/tests/test_execution_integration.py -x`. Browsers: `npm.cmd test --prefix frontend -- ads.spec.ts attribution.spec.ts breakout.spec.ts budget.spec.ts clearance.spec.ts cohorts.spec.ts commerce.spec.ts decisions.spec.ts diagnostics.spec.ts finance.spec.ts foundation.spec.ts inventory.spec.ts`. Execution mutation cases excluded. Source-changing checks run sequentially; fresh source preparation uses isolated IDs and no proposal/approval/execution methods, restoring defaults in `finally`.
- Actual outage stops/starts the existing deployment in `finally`, preserves private/TLS/launcher/state/volumes, then restores `probe`, default `refresh`, `commerce`, `ads`, `attribution`, `finance`, `inventory`, `diagnostics`. Run `scripts/verify-decisions-state.py` for inherited A18/A19/A20/A21/default/action checks plus unified decisions and six full action/state/control and five original private-file hash comparisons. Preserve every audit row. INR 0; no publishing, advertising mutations, paid services or later module. Phase 14 needs another requested chat. Record final executed results in the Phase 13 handoff.

Phase 13 final verification October 31: **249 isolated passes / twenty-two real-store skips**, **269-pass/no-skip broad non-mutating real-store regression**, then **one focused real-store pass / one deselected** for retained fresh-review invalidation. Separate commands, not a single final 270-test run. Final authenticated healthy and actual-stopped-Exasol browsers each **fifteen passed / twelve mode skips**, covering **27 cases** (two rendering substitutes). An initial healthy finance null-data dereference, stricter availability assertions and passing focused/final reruns are documented; underlying cause remains unverified. All seven defaults restored; **nineteen unique default decisions abstain**, five budgets retain **1,100,000 paise / INR 11,000 daily**. **Three retained recommendation observations / zero explicit action links**, financial effects unknown. Historical stock/diagnostic/breakout/cohort counts and cutoffs unchanged; **60 exact approved receipts**, zero invalid/orphan receipts/unresolved intents. **Six full action/state/control hashes** and **five original private/TLS/launcher/deployment/unrelated-file hashes** unchanged. Existing volumes/state reused; all listeners loopback; no publishing, advertising mutation, paid service/provisioning, reset or cleanup; INR 0. Only synthetic local conflict/tracking is verified. Phase 14 requires another requested chat.



Current Phase 12: the user separately authorized only Budget optimization on October 31 IST. Read the ordered baseline using [Phase 11 handoff](docs/handoffs/phase-11.md), Phase 12 plan and [budget contract](docs/phase-12-budget.md); current work is recorded in [Phase 12 handoff](docs/handoffs/phase-12.md). Its synthetic local A21 gate passed October 31. Earlier unstarted statements are historical. Only Phase 12 may close here; Phase 13 requires another user-requested chat. The October 30, 23:59 IST deadline has passed; report actual verification dates.

## Phase 12 budget commands and boundaries

- Phase 12 alone is separately authorized October 31. Read [budget contract](docs/phase-12-budget.md). Authenticated GET `/api/budget` and origin-protected POST `/api/budget/scenario` reuse six coherent pinned inputs and ephemeral strict terms. Existing fixed INR total; configurable downward from maximum 1,000-basis-point change bound; exact paise, no extrapolation. No new schema/importer/worker/cache/publication pointer, saved recommendation or action interface.
- Complete contiguous India-day half-hour reporting, sufficient repeated spend levels, mature 60-day all-attributed-order outcomes and known costs gate the descriptive response envelope. Sparse bundled reports abstain. Assume full budget delivery explicitly; sensitivity is not confidence, calibrated LTV, causal/incremental profit or a predictive backtest. Keep cohort mature/immature/missing-cost/history coverage separate. No future costs/events or covered-only subtotal substitution.
- Exact whole-budget members/mappings, clear fresh inventory for every affected product, active hierarchy/durable state, fresh ads/diagnostics/resource observations and cleared destinations gate reallocation. Blocked resources freeze without endorsing an unsafe baseline. Kill switch, unresolved intents, changed pins/state/revisions and clock transitions block comparisons. Read-only state snapshots must never initialize/reset the simulator or create action/approval records. Every future advertising mutation still needs separately persisted exact explicit approval and Phase 8 revalidation.
- Isolated checks use `.\.venv\Scripts\python.exe -m pytest -q`. Private real-store regression uses `RUN_INTEGRATION=1` and `.\.venv\Scripts\python.exe -m pytest -q --ignore=backend/tests/test_execution_integration.py -x`. Browser command: `npm.cmd test --prefix frontend -- ads.spec.ts attribution.spec.ts breakout.spec.ts budget.spec.ts clearance.spec.ts cohorts.spec.ts commerce.spec.ts diagnostics.spec.ts finance.spec.ts foundation.spec.ts inventory.spec.ts`. Execution mutation cases excluded. Run source-changing checks sequentially and wait for completion before another importer. Fresh stockout checks reuse only source preparation under isolated IDs and restore defaults; no approval/execution method is called.
- Actual outage stops/starts the existing deployment in `finally`, preserving private/TLS/launcher/volumes/history, then restores `probe`, default `refresh`, `commerce`, `ads`, `attribution`, `finance`, `inventory`, `diagnostics`. Run `scripts/verify-budget-state.py` for inherited A18/A19/A20/default/action audit plus budget reconciliation. Check original private file hashes and six full action/state/control table hashes. No publishing, advertising mutation, paid API/provisioning, billing change or ledger cleanup; INR 0. Phase 13 needs another requested chat. Final executed evidence belongs in the Phase 12 handoff.



Phase 12 final verification October 31: **208 isolated passes/twenty real-store skips**, **22 focused policy/API passes**; **226-pass/no-skip broad non-mutating real-store regression**, followed by **one focused real-store pass/two deselected** for the inclusive proof boundary. Separate commands, not a single final 227-test run. Authenticated healthy and actual-stopped-Exasol browsers each **fourteen passed/eleven mode skips**, covering 25 cases (two rendering substitutes); execution mutations excluded. All seven defaults/healthy stores restored. Five distinct default budgets retain **1,100,000 paise/INR 11,000 per day**, all frozen because response evidence is unsuitable. A21 high-response attractiveness is controlled policy evidence; fresh real stockout independently blocks exact whole-budget growth. Final inherited A18/A19/A20/default/action audit passes; historical stock/diagnostics/breakout/cohort counts/cutoffs unchanged. **60 retained exact approved receipts**, zero invalid/orphan receipts/unresolved intents; **six full action/simulator/control table hashes** and **five original private/TLS/launcher/deployment/unrelated-file hashes** unchanged. All listeners loopback; existing volumes/state reused; no publishing, advertising mutation, paid API/provisioning, reset or ledger cleanup; INR 0. Only synthetic local budget optimization is verified. Phase 13 remains unstarted and requires another requested chat.

## Start each phase



Read, in order: `docs/project-status.md`, the latest file in `docs/handoffs/`, `docs/product-specification.md`, `docs/architecture.md`, and the relevant entry in `docs/phase-plan.md`. Read linked detailed contracts before changing business behavior.



- Work on one phase per chat. Phase 0 is closed as a planning deliverable; Phase 1's local foundation gate passed October 27. Phase 2's commerce and Phase 3's ad-reporting gates passed October 30 in separate user-requested chats. Phase 4's mapping/attribution gate passed October 30 in its own user-requested chat. Phase 5's synthetic local finance gate passed October 30 in its own user-requested chat. Phase 6's synthetic local inventory gate passed October 30 in its own user-requested chat. Phase 7's synthetic local diagnostic gate passed October 30 in its own user-requested chat; Phase 8's synthetic local approved-execution gate passed October 30 in its own user-requested chat. Phase 9 requires another user-requested chat. Do not advance automatically. Read current status; do not silently advance or create another chat.

- Confirm the active phase and its acceptance criteria from the handoff. Reuse established decisions; ask only for unresolved information that affects the work.

- User requirements override proposed defaults. Distinguish accepted requirements, proposed defaults, implemented behavior, and verified behavior.



## Project boundaries



- Deadline: October 30, 2026, 23:59 Asia/Kolkata. Check current status; an old target date is not evidence of completion.

- Single Indian apparel merchant, one warehouse, INR domestic sales, prepaid/COD, returns/RTO.

- Demo uses synthetic commerce/ad data, real Exasol analytics, and simulated platform actions. Never claim live integration or model effectiveness from fixture tests.

- Every advertising mutation, including pause/resume, requires explicit approval.

- Prototype infrastructure/API charges must remain INR 0. User supplied AWS Free-plan console text: USD 139.73 credits, free access until Feb 3, 2027 or depletion. Reconfirm before provisioning. Do not upgrade billing or assume budget alerts prevent charges. See `docs/phase-0/deployment-decision.md` for preflight and default-instance incompatibility.

- Local Exasol and whole-application local fallback are accepted (user confirmed October 27 in Phase 1). AWS provisioning still requires full preflight and current balance confirmation.

- Exasol-specific SQL/connection details belong in the analytics adapter. Operational state belongs in PostgreSQL. See architecture and metric contracts.

- Preserve unrelated user files, including `architecture_diagram_v0.1(initial)`.



## Commands and verification



- Repository inspection: `git status --short`, `rg --files`, `git diff --check`.

- Setup: `python -m venv .venv`, `.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt`, `.\.venv\Scripts\python.exe -m pip install -e . --no-deps`, `npm.cmd ci --prefix frontend`. Windows blocks the native SQLAlchemy extension: use its supported pure-Python build (`DISABLE_SQLALCHEMY_CEXT=1` during source install); see `docs/phase-1-setup.md`. Rollup uses the official WASM package via the locked npm alias.

- Verified commands: `.\.venv\Scripts\python.exe -m pytest -q` (isolated tests; real integration skipped unless explicitly configured), `.\.venv\Scripts\python.exe scripts/export_openapi.py`, `npm.cmd run types --prefix frontend`, `npm.cmd run build --prefix frontend`, `.\.venv\Scripts\python.exe -m pip check`, `.\.venv\Scripts\python.exe -m compileall -q backend scripts`.

- Browser checks: `.\.venv\Scripts\python.exe scripts/serve-preview.py`, then `npm.cmd test --prefix frontend`. Uses installed Chrome (override `PLAYWRIGHT_CHANNEL` if needed); preview has unreachable databases. UI route substitutes are rendering checks only; real authenticated browser test requires private `E2E_OPERATOR_PASSWORD` and actual stores.

- Database setup/runtime commands are in `docs/phase-1-setup.md`. Do not claim the Phase 1 gate from skipped integration tests, fixture responses or a frontend build. Set `RUN_INTEGRATION=1` only against dedicated real database configuration.

- Real local commands verified October 27: load private environment with `. .\scripts\env.ps1`; run `.\.venv\Scripts\python.exe -m advergent.worker migrate`, `probe`, and `refresh`; run the API with `.\.venv\Scripts\python.exe -m uvicorn advergent.api:create_app --factory --host 127.0.0.1 --port 8000`. With `RUN_INTEGRATION=1`, backend suite passed all 6 tests against real stores. Browser suite with private operator environment passed in healthy and actual-Exasol-outage modes; exact commands/limits are in `docs/handoffs/phase-1.md`.

- Validate untracked files too: `.\scripts\check-docs.ps1` and `.\.venv\Scripts\python.exe scripts/check-files.py`. Exasol's local launcher suggests `nocertcheck`; do not use it. Pin the certificate copied from the trusted local container. Preserve launcher `.exasol` state, private `.env`/`.runtime` credentials and persistent volumes when resuming.

- Phase 2 commands after loading private environment: `.\.venv\Scripts\python.exe -m advergent.commerce_fixture` deterministically regenerates the source; `worker migrate` applies all migrations including commerce; `.\.venv\Scripts\python.exe -m advergent.worker commerce` imports/replays it (`--fixture PATH` selects another immutable source). Source observation drives freshness; replay must not make historical inventory fresh. Separate foundation and commerce publication pointers are intentional. See `docs/phase-2-commerce.md` and `docs/handoffs/phase-2.md`.

- Phase 3 commands after loading private environment: `.\.venv\Scripts\python.exe -m advergent.ads_fixture` regenerates both deterministic report histories; `worker migrate` applies all three migrations; `.\.venv\Scripts\python.exe -m advergent.worker ads --fixture fixtures/ads-initial-v1.json` selects initial reports; `worker ads` imports/replays the default corrected source. Namespace `ads-schema-v2:` identifies normalization. INR uses exact paise; synthetic closed half-hour UTC grains retain source dates and derive Asia/Kolkata days. Higher revisions replace, never append, same-grain spend. Separate ad publication/cursors/source staging live in PostgreSQL; actual spend/hierarchy queries use Exasol. Source product references are unverified hints, not commerce mappings. See `docs/phase-3-ad-reporting.md` and `docs/handoffs/phase-3.md`.

- Phase 3 real-store suite passed 37 tests with `RUN_INTEGRATION=1`; browser suite passed six tests in each healthy/outage mode (three mode-specific skips each, all nine distinct tests executed across modes). Real browser ad tests import initial/corrected fixtures and deliberately fail an SQL load, restoring the default corrected publication in `finally`. Inherit private database environment and `E2E_OPERATOR_PASSWORD`; never run healthy-mode source-import checks while Exasol is deliberately stopped. No live API or action capabilities are verified.

- Phase 4 commands after loading private environment: `.\.venv\Scripts\python.exe -m advergent.attribution_fixture` regenerates mapping/click/claim evidence; `worker migrate` applies migration 004; `.\.venv\Scripts\python.exe -m advergent.worker attribution` publishes against pinned commerce/ad inputs (`--fixture PATH` selects another complete configuration). PostgreSQL owns immutable configuration/override snapshots; analytical relationships and order allocations live in Exasol. Namespace `attribution-v1:` includes both upstream dataset IDs. Native hints never become mappings. Seven-day last-paid-click and 9,000-basis-point confidence are visible implementation defaults. See `docs/phase-4-mapping-attribution.md` and `docs/handoffs/phase-4.md`.

- Phase 4 real-store suite passed 50 tests; isolated run passed 46 with four integration skips. Browser healthy mode passes seven tests/four outage skips; actual outage mode passes seven/four healthy skips, covering all eleven cases (two are rendering substitutes only). The attribution browser test imports/replays and induces a genuine SQL failure, restoring default attribution in `finally`. Run healthy imports only with Exasol running. First-party placed merchandise is not full finance or proven incremental profit. Phase 5 was unstarted at that historical handoff; its later gate is documented below.

- Phase 5 commands after loading private environment: `.\.venv\Scripts\python.exe -m advergent.finance_fixture` regenerates complete expense/settlement/recovery evidence; `worker migrate` applies migration 005; `.\.venv\Scripts\python.exe -m advergent.worker finance` publishes against current matching pinned attribution/commerce/ad inputs (`--fixture PATH` selects another complete source). Namespace `finance-v3:` includes attribution identity; PostgreSQL retains immutable configuration/attempts, Exasol owns typed lines/events and actual SQL economics/date/campaign reconciliation. See [finance contract](docs/phase-5-finance.md) and [Phase 5 handoff](docs/handoffs/phase-5.md).

- Phase 5 final real-store suite passes 61 tests; isolated passes 56 with five integration skips. Authenticated healthy and actual-stopped-Exasol browser modes each pass eight tests/five mode-specific skips, covering all thirteen cases (two inherited rendering substitutes). Finance browser checks import/replay/correct and deliberately fail actual SQL; default finance restores in `finally`. Run all source-mutating checks sequentially, only with Exasol healthy. Restore launcher/state, probe and default foundation/commerce/ads/attribution/finance publications after actual outage.

- Finance keeps missing costs/unknown recovery null; covered-only subtotals are not complete contribution. Default delivery timing, 30-day/10%/80%/INR 50 return assumptions are labelled synthetic implementation defaults, not calibrated merchant settings. Source cutoffs differ; snapshot MER over bounded synthetic reports does not prove full merchant-period coverage. Historical corrections explicitly target effective lines and preserve originals. No contribution is incremental profit. That Phase 5 handoff is historical; Phase 6 is now authorized in its own inventory chat.

- Run checks appropriate to the phase. Record command, date, result, and important limitations in the handoff. Untracked files are not covered by ordinary `git diff --check`; check new documents explicitly.

- Never record credentials, tokens, account IDs, or sensitive billing screenshots in repository documents.



## Finish every phase



1. Update product specification for scope/rule decisions and architecture for component/interface decisions.

2. Update phase requirements, acceptance status, and dependency changes in `docs/phase-plan.md`.

3. Update `docs/project-status.md` with completed work, unverified work, checks, known issues, and next steps.

4. Create/update `docs/handoffs/phase-N.md`: changes, decisions, files, tests/results, limitations, unresolved questions, and next-phase prerequisites.

5. Update these instructions with real commands and changed rules. Preserve prior handoffs; record later corrections explicitly.

6. Every completed phase must end with a ready-to-use starter prompt for the next phase, in its handoff and at the end of the final response. Do not start that phase automatically.

7. Mark completion only when the phase gate is met. Documentation written, a test planned, or a feature mocked is not equivalent to verified functionality.



Use `docs/handoffs/README.md` for the handoff format. Do not require the user to repeat earlier context when repository documents contain it.





## Phase 6 inventory commands and boundaries



- After private environment loading, `.\.venv\Scripts\python.exe -m advergent.inventory_fixture` regenerates deterministic warehouse evidence; `worker migrate` applies migration 006; `.\.venv\Scripts\python.exe -m advergent.worker inventory` publishes against pinned matching finance/attribution/commerce/ad inputs (`--fixture PATH` for another complete immutable source). Namespace `inventory-v1:` includes finance identity. PostgreSQL owns immutable configuration/simulated resource provenance, attempts and publication; Exasol owns typed observations and actual stock/rate/cover/weighted-size SQL. See [inventory contract](docs/phase-6-inventory.md) and [handoff](docs/handoffs/phase-6.md).

- Warehouse demand/exposure counters are independent synthetic observations, not additional commerce orders or revenue. No replay renews source freshness. Available already excludes commitments; subtract only the separate reserve once. Sparse/zero/missing exposure and unknown leads remain uncertain. Receipts are not current stock. Imported simulated prior pause evidence is not an implemented Phase 8 action ledger.

- Every recommendation exposes approval-required/mutation-disabled status. Recovery requires prior AdVergent pause evidence and cleared blockers; merchant/unknown pauses cannot recover. Exact reviewed valid mapping and capabilities constrain resources; a product-only stockout cannot broaden mixed-resource pause. Finance context retains missing costs and is not incremental profit. No advertising write or Phase 7/8 module is authorized.

- Run source-mutating integration/browser checks sequentially with Exasol healthy. After actual outage, preserve launcher/TLS pin/volumes and restore probe plus default `refresh`, `commerce`, `ads`, `attribution`, `finance`, `inventory` publications before final healthy checks. Exact executed counts belong in the Phase 6 handoff. Phase 7 requires a new user-requested chat.



- Phase 6 final verification October 30: backend real-store suite **87 passed/no skips**; isolated **81 passed/six skips**. Authenticated healthy and actual-stopped-Exasol browser modes each pass **nine tests/six mode-specific skips**, covering all fifteen distinct cases (two inherited rendering substitutes). Healthy browser inventory checks import fresh/receipt/arithmetic/recovery/blocked sources and induce actual SQL failure, restoring default inventory in `finally`. All six default publications and healthy stores were restored afterward; final default inventory is 180 variants/8,817 sellable units with historical observations still stale. Read the Phase 6 handoff for exact commands, evidence levels and limits. Phase 7 remains unstarted.





## Phase 7 diagnostics commands and boundaries



- After loading private environment, `.\.venv\Scripts\python.exe -m advergent.diagnostics_fixture` regenerates deterministic source evidence; `worker migrate` applies migration 007; `.\.venv\Scripts\python.exe -m advergent.worker diagnostics` publishes against pinned matching inventory/finance/attribution/commerce/ad inputs (`--fixture PATH` selects another complete immutable source). Namespace `diagnostics-v1:` includes inventory identity. PostgreSQL owns immutable configuration, attempts and publication; Exasol owns typed destination/window observations, selected-variant joins and CTR evidence. See [diagnostics contract](docs/phase-7-diagnostics.md) and [handoff](docs/handoffs/phase-7.md).

- No crawling or model calls: URLs/redirect targets, catalog titles and page text remain inert escaped evidence. Repeated fresh spaced 404s differ from transient/server/bot uncertainty. Selected-variant identity, unknown prices, archive and expiry remain distinct. Comparable adjacent seven-day windows and explicit floors are uncalibrated implementation defaults; possible fatigue is descriptive only.

- Creative review suggestions use fixed templates with pinned structured catalog size/color facts, valid exact reviewed mappings, current coherent dependencies and clear fresh inventory for every affected product. Destination/price/catalog/mapping/inventory blockers withhold suggestions. Low-confidence native hints never become reviewed scope. Capabilities/shared-budget members remain explicit; all reviews are advisory, approval-required and mutation-disabled.

- Run source-mutating integration/browser checks sequentially with healthy Exasol. The real variant-price case temporarily imports a complete commerce version with differently priced variants of one product and republishes coherent downstream sources; `finally` restores defaults. Browser diagnostics imports fresh and clear-inventory scenarios, induces genuine SQL failure and restores default inventory/diagnostics in `finally`.

- After actual outage, preserve existing launcher/TLS pin/volumes and restore `probe`, then default `refresh`, `commerce`, `ads`, `attribution`, `finance`, `inventory`, `diagnostics` before final healthy checks. No advertising writes, Phase 8 implementation, later modules, provisioning or paid API use in Phase 7. Charges remain INR 0. The earlier Phase 6 statement that Phase 7 was unstarted is historical; Phase 7 is now explicitly authorized in this chat. Phase 8 requires a new user-requested chat.



- Phase 7 final verification October 30: backend real-store suite **114 passed/no skips**; isolated **106 passed/eight skips**. Authenticated healthy and actual-stopped-Exasol browser modes each pass **ten tests/seven mode-specific skips**, covering all seventeen distinct cases (two inherited rendering substitutes). Focused diagnostic browser flow also passes. Exact retry/freshness/CTR floors, real same-product distinct variant prices, escaped malicious evidence, catalog/mapping/inventory/capability grounding, actual SQL rollback/orphan reuse/typed corruption and pin changes pass. Existing stores/TLS pin/state/volumes and all seven defaults are restored; direct queries confirm two diagnostic reviews/eleven observations/four windows/zero suggestions with historical source evidence still stale, and unchanged 180 variants/8,817 sellable units. Read the Phase 7 handoff for exact commands, evidence levels and limitations. Phase 8 remains unstarted.





## Phase 8 execution commands and boundaries



- Phase 8 is explicitly authorized in its own October 30 chat; earlier unstarted statements are historical. Only Phase 8 may be implemented here. After private environment loading, `worker migrate` applies migration 008. No simulator mutation occurs without a separately persisted exact explicit approval. Source imports and recommendations never grant consent.

- Read [execution contract](docs/phase-8-approved-execution.md). All six analytical dependency IDs, exact resource/status/integer INR paise, whole-member mappings/capabilities, expected simulator revisions and expiry bind approvals. Default lifetime is 30 minutes; actual UTC controls expiry/freshness. Unknown execution retries reconcile by read-back only, reserving affected keys; new recovery mutations need new approval. Kill switch blocks new writes, including a transfer recipient after donor success.

- Execute source-mutating checks sequentially with healthy Exasol. `backend/tests/test_execution_integration.py` and `frontend/tests/execution.spec.ts` use isolated synthetic resource IDs and explicit test approvals, retaining durable audit. `execution_scenarios.prepare` creates source observations only; `restore` republishes default ads/attribution/finance/inventory/diagnostics. Preserve all ledger/history and private configuration.

- After actual outage restore existing deployment/TLS pin/state/volumes, probe and all seven default publications before final healthy checks. No live advertising writes, provisioning, paid API, billing change or later module. INR 0. Phase 9 requires a new user-requested chat. Final gate counts belong in the Phase 8 handoff.



- Phase 8 clock/state rule: every new plan binds `clock_valid_until` to the next relevant evidence/mapping/offer boundary. Actual simulator SQL must enforce proof and approval expiry at the write; revalidation cannot refresh consent or evidence. A recipient transaction must lock/verify earlier successful resources at their expected post-write revision/request. Legacy development plans without the clock field require a new proposal for any new write.





- Phase 8 final verification October 30: isolated **130 passed/ten skips**; full real-store regression **138 passed/no skips**, then final execution/atomic clock **two passed**, and final post-donor-edit guard follow-up **one passed/one deselected**. These are separate commands; never claim a single final 140-test run. Authenticated healthy browser **12 passed/eight mode skips**; actual-stopped-Exasol **11 passed/nine mode skips**, covering all twenty cases (two inherited rendering substitutes). Post-restart read-only authenticated smoke passes. All seven defaults/coherent pins and healthy stores/TLS state/volumes restored; inventory180/8,817, diagnostic2/11/4/zero suggestions remain historical/stale. Audit60 exact approved receipts, zero orphan/invalid receipts and zero unresolved intents. Intermediate communication failure/restart and test harness corrections are documented in the Phase 8 handoff. Only synthetic local execution is verified; production/live fidelity is not. Phase 9 remains unstarted and needs another user-requested chat.



## Phase 9 clearance commands and boundaries



- Phase 9 is separately authorized in this chat; earlier unstarted statements are historical. Read [clearance contract](docs/phase-9-clearance.md). No clearance migration/importer/worker or persistent scenario publication exists. Authenticated GET `/api/clearance` calculates default A18; origin-protected POST `/api/clearance/scenario` accepts ephemeral strict terms and returns them with five pinned IDs/source cutoffs. PostgreSQL retains existing operational configuration/publications; actual stock/catalog joins and demand features come from Exasol. No analytics fallback.

- Uniform stock-age, horizon/holding, explicit bundle sales, variable expense and net return loss are uncalibrated synthetic assumptions. No response model links markdown/spend to sales. Baseline uses the same mix at full price with zero additional spend. Current prospective catalog COGS never replace historical finance costs/reserves. Unknown required costs preserve unknown contribution/delta. Enforce every component's sellable stock, nonnegative configurable contribution floor and exact margin floor; zero-revenue margin is undefined. Insufficient demand remains unranked/uncertain. Stale selected stock/changed inputs block feasibility. Every comparison remains publishing/mutation disabled even if feasible.

- Run `.\.venv\Scripts\python.exe -m pytest -q` for isolated checks. Real-store non-mutating regression uses private environment and `RUN_INTEGRATION=1` with `.\.venv\Scripts\python.exe -m pytest -q --ignore=backend/tests/test_execution_integration.py -x`. For browsers inherit private `E2E_OPERATOR_PASSWORD` and use `npm.cmd test --prefix frontend -- ads.spec.ts attribution.spec.ts clearance.spec.ts commerce.spec.ts diagnostics.spec.ts finance.spec.ts foundation.spec.ts inventory.spec.ts`. This explicit list excludes execution; Playwright has no generic `--ignore` file option. Do not run execution integration/browser cases that mutate advertising state in this phase. Clearance real-store fresh-stock/pin checks temporarily publish explicitly new synthetic inventory and initial ads, restore defaults in `finally`, and grant no approval/action.

- Run source-changing real/browser checks sequentially with healthy Exasol. For actual outage, stop/start the existing deployment in `finally`, preserve TLS/private/launcher/volumes, and restore `probe`, default `refresh`, `commerce`, `ads`, `attribution`, `finance`, `inventory`, `diagnostics`. `.\.venv\Scripts\python.exe scripts/verify-clearance-state.py` performs read-only coherent default/A18/diagnostic/receipt checks. Keep all action history; no simulator reset or ledger cleanup. INR 0; no publishing, advertising mutation, provisioning or later module. Phase 10 needs another user-requested chat.

- October 30, 2026, 23:59 IST deadline has passed; Phase 9 verification completed October 31. Exact dated gate counts/restoration/limitations belong in the Phase 9 handoff; do not turn planned tests into completion claims.

- Phase 9 final verification October 31: **151 isolated passes/twelve real-store skips**, final **21 focused policy/API passes**; **160-pass/no-skip broad non-mutating real-store regression**, then **two passing final focused clearance tests**. Separate commands; do not claim one final 161-test run. Authenticated healthy and actual-stopped-Exasol browsers each **eleven passed/eight mode skips**, covering nineteen cases (two inherited rendering substitutes); mutation-performing execution cases excluded. All seven defaults and healthy stores restored; stock180/8,817 and diagnostics2/11/4/zero suggestions remain historical/stale. **60 retained receipts**, zero invalid/orphan receipts/unresolved intents. Private environment/TLS/launcher secrets/deployment configuration/unrelated-file hashes unchanged. No publishing or advertising mutations; INR 0. Only synthetic local clearance is verified; Phase 10 remains unstarted.



## Phase 10 breakout commands and boundaries



- Phase 10 alone is authorized. `.\.venv\Scripts\python.exe -m advergent.breakout_fixture` deterministically regenerates raw historical events/coverage; `worker migrate` creates the analytical BR_EVENTS/BR_SOURCES tables. Authenticated GET `/api/breakout` selects the bundled content-addressed source, transactionally caches and fully verifies deduplicated typed evidence in Exasol, and returns five pinned upstream IDs/cutoffs. There is no new operational publication pointer or action interface. See [breakout contract](docs/phase-10-breakout.md).

- Evidence floors, comparable seven-day windows/tracking series, complete nonnegative historical contribution margin and fresh clear inventory gate every rank. Missing costs, sparse/unknown coverage, stale/future evidence and changed pins abstain. Later time-window evaluation never enters the score and does not prove predictive/causal effectiveness. Purchases must reference existing order/product pairs; callbacks deduplicate and add **zero** revenue. All publishing/mutation flags remain false. No precise budget forecast or later module.

- Run isolated tests normally; real-store regression after private environment loading uses `RUN_INTEGRATION=1` and `.\.venv\Scripts\python.exe -m pytest -q --ignore=backend/tests/test_execution_integration.py -x`. Run real source-changing checks sequentially. Authenticated browser command: `npm.cmd test --prefix frontend -- ads.spec.ts attribution.spec.ts breakout.spec.ts clearance.spec.ts commerce.spec.ts diagnostics.spec.ts finance.spec.ts foundation.spec.ts inventory.spec.ts`. Explicit list excludes mutation-performing execution cases.

- Actual outage must stop/start the existing deployment in `finally`, preserve private configuration/TLS/launcher/volumes/action history, then probe and restore default `refresh`, `commerce`, `ads`, `attribution`, `finance`, `inventory`, `diagnostics`. `.\.venv\Scripts\python.exe scripts/verify-breakout-state.py` performs read-only inherited A18/default/diagnostic/action audit plus A19 checks. INR 0; no publishing, advertising mutation, provisioning, paid API or ledger cleanup. Phase 11 requires another requested chat. Final executed counts belong in the handoff.


- Phase 10 final verification October 31: **172 isolated passes/fifteen real-store skips**, **21 focused policy/API passes**; **182-pass/no-skip broad non-mutating real-store regression**, then **three focused real-store passes** including final SQL rollback/retry. Separate commands, not a claimed single final 185-test run. Authenticated healthy and actual-stopped-Exasol browsers each **twelve passed/nine mode skips**, covering 21 cases (two inherited rendering substitutes); execution mutations excluded. All seven defaults/healthy stores restored; stock180/8,817, diagnostics2/11/4/zero suggestions and default breakout30 products/zero ranks remain historical/stale. Raw7,479/unique7,478 events; one duplicate, zero added revenue. **60 retained exact approved receipts**, zero invalid/orphan receipts/unresolved intents. All five private/TLS/launcher/deployment/unrelated-file hashes unchanged; no publishing, advertising mutation, paid API/provisioning or ledger cleanup; INR 0. Only synthetic local breakout is verified. Phase 11 remains unstarted.

## Phase 11 cohort commands and boundaries

- Phase 11 alone is separately authorized October 31. Read [cohort contract](docs/phase-11-cohorts.md) and [handoff](docs/handoffs/phase-11.md). Authenticated GET `/api/cohorts` reuses four coherent pinned finance/commerce/ads/attribution IDs; optional aware `as_of` only moves the earliest observed cutoff earlier. No migration/importer/worker/cohort publication or action interface exists.
- First observed delivery uses actual finance delivery time, lexical order ID for ties, first-order net merchandise rational product weights, and exact largest-remainder paise. Bounded history is incomplete; zero-value assignment abstains. Half-open rolling 60/90-day actual event windows keep mature/immature month/product buckets separate. Acquisition pre-delivery expenses count once; refunds/recoveries retain event dates. Missing costs remain null; covered event/known customer subtotals are not full estimates or bounds. Cash, reserves, ads and funnel events never become contribution. Retrospective snapshots do not prove historical knowledge or calibrated LTV.
- Real-store command after private environment loading: `RUN_INTEGRATION=1`, `.\.venv\Scripts\python.exe -m pytest -q --ignore=backend/tests/test_execution_integration.py -x`. Authenticated browser command: `npm.cmd test --prefix frontend -- ads.spec.ts attribution.spec.ts breakout.spec.ts clearance.spec.ts cohorts.spec.ts commerce.spec.ts diagnostics.spec.ts finance.spec.ts foundation.spec.ts inventory.spec.ts`. Exclude execution mutations. Run source-changing checks sequentially and wait for command completion before another importer.
- Actual outage must stop/start the existing deployment in `finally`, preserve private/TLS/launcher/volumes/action history, then probe and restore default `refresh`, `commerce`, `ads`, `attribution`, `finance`, `inventory`, `diagnostics`. Run `scripts/verify-cohorts-state.py` for inherited A18/A19/default/action audit and A20. No publishing, advertising mutations, paid API/provisioning or ledger cleanup; INR 0. Phase 12 requires another requested chat. Final executed evidence belongs in the handoff.

- Phase 11 final verification October 31: **186 isolated passes/seventeen real-store skips**, **14 focused policy/API passes**; **198-pass/no-skip broad non-mutating real-store regression**, then final **two focused real-store passes** after the exclusive correction-boundary guard. Separate commands, not a single final 201-test run. Authenticated healthy and actual-stopped-Exasol browsers each **thirteen passed/ten mode skips**, covering 23 cases (two rendering substitutes); execution mutations excluded. Shared browser assertion wait is 30 seconds because simultaneous initial analytical requests/queued logout can exceed five seconds; exact assertions remain unchanged, production responsiveness unverified. Import-lock/harness/timing corrections are in the handoff.
- Final read-only audit: **715 assigned / 285 ordering customers without delivery / 26 multi-product**, zero zero-value unassigned; **60-day 629 mature/86 immature/twelve missing-cost windows**, **90-day 565 mature/150 immature/fifteen missing-cost windows**. Fractions/known paise reconcile; history incomplete, cutoff October 29 18:00 UTC. All seven defaults/healthy stores restored, stock180/8,817, diagnostics2/11/4/zero suggestions, breakout30/zero ranks historical/stale. **60 retained exact approved receipts**, zero invalid/orphan receipts/unresolved intents; all five private/TLS/launcher/deployment/unrelated-file hashes unchanged, listeners loopback, existing volumes/state reused. No publishing, advertising mutation, paid API/provisioning or ledger cleanup; INR 0. Only synthetic local cohorts verified; Phase 12 remains unstarted.
