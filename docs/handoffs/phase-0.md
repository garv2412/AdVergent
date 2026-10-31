# Phase 0 handoff

Updated: 2026-10-27. Status: **complete as a planning/research phase; deployment and runtime execution not verified**.

## Changes and deliverables

- [Phase 0 baseline](../phase-0/README.md): accepted objective, exclusions, defaults, cost contract.
- [Metric contract](../phase-0/metric-contract.md): proposed ledger, attribution, inventory, model, and approval semantics.
- [Verification plan](../phase-0/verification-plan.md): A01–A26, capability matrix, AWS risks, initial deadline targets.
- [Deployment decision](../phase-0/deployment-decision.md): updated AWS evidence, versioned Exasol requirements, local prerequisite findings, conditional hosting route, and Phase 1 stop conditions.
- [Product specification](../product-specification.md), [architecture](../architecture.md), [phase plan](../phase-plan.md), and [status](../project-status.md): persistent navigation and current state.
- [AGENTS.md](../../AGENTS.md): project rules and per-phase documentation requirements.

No application or infrastructure changes. User-owned `architecture_diagram_v0.1(initial)` was not edited. Planning documents are currently untracked; no commit or push has been performed in this chat.

## Decisions

Confirmed: single merchant evolving toward SaaS; Indian apparel/footwear, one warehouse, INR domestic sales, prepaid/COD and RTO; real Exasol analytics with replaceable adapter; synthetic sources/actions across four pillars; approval for every mutation; INR 0 charges; cloud credits permitted with charge prevention; local Exasol fallback; deadline Oct 30 at 23:59 IST; separate chat per phase.

User supplied AWS console text: USD 139.73, 101 displayed days, free access ending February 3, 2027 or credit depletion, with an upgrade option. This supports Free-plan status and supersedes the earlier approximate USD 100/unknown-plan record. No authenticated cloud inspection occurred. AWS is preferred conditionally; preserve Free-plan status and validate compatible resources before provisioning.

React/Vite, FastAPI, PostgreSQL, detailed numerical policies, fixture size, delivery-based revenue recognition, and attribution windows remain proposed defaults. No live accounts or history are available.

## Checks and results

- Repository/read inspection completed on 2026-10-27 using `git status --short`, `rg --files -g '*.md' -g '!node_modules'`, and document reads. Planning files exist; no runtime/test commands established.
- Earlier `git diff --check` returned exit 0 but did not inspect untracked documents.
- 2026-10-27 inline PowerShell documentation check: exit 0; 11 Markdown files inspected, 25 local links resolved, no trailing whitespace, and 26 unique A01–A26 cases found. Checked untracked files directly. This verifies document structure, not application behavior. Reproducible command is below.
- No application tests, database queries, deployment tests, acceptance scenarios, or live API tests run. Documentation research is feasibility evidence only.
- Read-only runtime probes on October 27: Windows 11 x64, 15.8 GiB RAM, 128.5 GiB free D: space, WSL2 and winget found. Podman/AWS CLI/Exasol absent from PATH. Docker CLI 29.6.2 found, daemon probe failed because Linux engine pipe was unavailable. No repair/install attempted. Exact commands and source links are in the deployment decision.
- Exasol release API and versioned v2.3.0 source reads succeeded. One guessed source path returned 404; GitHub tree inspection located `variables_public.tf`. GitHub Pages reads were unavailable through the web tool; versioned GitHub source resolved requirements. No external installer executed.
- Closeout documentation checks on October 27: exit 0; 12 Markdown files inspected directly, 33 local links resolve, no trailing whitespace, and 26 unique A01–A26 cases. The checker below was rerun; `git diff --check` also returned exit 0. These are documentation checks only. No commits/pushes performed.

## Exit-gate interpretation and limitations

Phase 0 establishes a concrete supported deployment/fallback plan and prerequisite evidence, not a working deployment. The earlier runtime-feasibility wording is clarified accordingly: AWS console evidence and current versioned requirements permit planning closeout, while actual account quota, compatible instance eligibility, full resource estimate, installation, connectivity, and loading remain mandatory Phase 1 gates. No runtime success is inferred.

Exasol's AWS preset defaults to r6i.xlarge and two 100 GB volumes, with archive integration enabled. That instance is not on AWS's published Free-plan list. Do not run unchecked defaults or upgrade to Paid to get past a restriction. Validate a compatible override, or prepare local Exasol using Podman. The local Windows route is documented in v2.3.0 but not tested on this host. Current detailed business rules remain proposed defaults.

Phase 0 closed October 27 rather than its October 26 target. Compressed remaining targets are in the deployment decision; Phase 1 must estimate feasibility/effort before promising completion. No original production phase is considered implemented by the planning closeout.

## Next phase prerequisites

At the start of the separate Phase 1 chat:

1. Read AGENTS.md, status, this handoff, and the deployment decision. Do not ask again for decisions already recorded.
2. Reconfirm AWS Free-plan/current credits through a user-authenticated method; inspect account permissions, region/quota, and compatible instance/resource plan read-only. Keep credentials outside repository/chat.
3. Review full credit consumption and network configuration before provisioning; choose the local Exasol fallback if AWS eligibility or sizing fails. Validate Podman prerequisites before local install.
4. Resolve hybrid connectivity only if fallback is used; ask about local whole-app operation if necessary. Re-estimate remaining deadline work.
5. Implement only the Phase 1 foundation slice and prove real connection/load/query behavior. Runtime checks and installations belong to that phase, not this completed planning phase.

First Phase 1 deliverable: authenticated UI -> typed API -> real Exasol query over a golden fixture, with operational state, failure reporting, and exact setup/test commands. Full financial module and live integrations are later scope.

## Documentation check command

Run in repository root with PowerShell. This is the executed checker formatted across lines for readability.

```powershell
$docPaths = @('AGENTS.md','README.md') + @(Get-ChildItem -LiteralPath docs -Recurse -Filter '*.md' | ForEach-Object { $_.FullName })
$docIssues = @()
$linkCount = 0
foreach ($docPath in $docPaths) {
    $resolvedDoc = (Resolve-Path -LiteralPath $docPath).Path
    $docText = [System.IO.File]::ReadAllText($resolvedDoc)
    foreach ($linkMatch in [regex]::Matches($docText, '\]\(([^)]+)\)')) {
        $linkTarget = $linkMatch.Groups[1].Value
        if ($linkTarget -match '^(https?://|#)') { continue }
        $linkCount++
        $linkPath = Join-Path (Split-Path -Parent $resolvedDoc) ($linkTarget.Split('#')[0])
        if (-not (Test-Path -LiteralPath $linkPath)) {
            $docIssues += "Broken link: $resolvedDoc -> $linkTarget"
        }
    }
    $lineNumber = 0
    foreach ($docLine in [System.IO.File]::ReadAllLines($resolvedDoc)) {
        $lineNumber++
        if ($docLine -match '[ \t]+$') { $docIssues += "Trailing whitespace: ${resolvedDoc}:$lineNumber" }
    }
}
$verificationText = Get-Content -LiteralPath docs/phase-0/verification-plan.md -Raw
$caseIds = @([regex]::Matches($verificationText, '(?m)^\| (A\d{2}) \|') | ForEach-Object { $_.Groups[1].Value })
if ($caseIds.Count -ne 26 -or @($caseIds | Select-Object -Unique).Count -ne 26) {
    $docIssues += 'Acceptance catalog does not contain 26 unique cases'
}
if ($docIssues.Count -gt 0) { $docIssues; exit 1 }
"PASS: $($docPaths.Count) Markdown files; $linkCount local links resolve; no trailing whitespace; A01-A26 contain 26 unique cases."
```
