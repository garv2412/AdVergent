$ErrorActionPreference = 'Stop'
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
        if (-not (Test-Path -LiteralPath $linkPath)) { $docIssues += "Broken link: $resolvedDoc -> $linkTarget" }
    }
    $lineNumber = 0
    foreach ($docLine in [System.IO.File]::ReadAllLines($resolvedDoc)) {
        $lineNumber++
        if ($docLine -match '[ \t]+$') { $docIssues += "Trailing whitespace: ${resolvedDoc}:$lineNumber" }
    }
}
$verificationText = Get-Content -LiteralPath docs/phase-0/verification-plan.md -Raw
$caseIds = @([regex]::Matches($verificationText, '(?m)^\| (A\d{2}) \|') | ForEach-Object { $_.Groups[1].Value })
if ($caseIds.Count -ne 26 -or @($caseIds | Select-Object -Unique).Count -ne 26) { $docIssues += 'Acceptance catalog does not contain 26 unique cases' }
if ($docIssues.Count -gt 0) { $docIssues; exit 1 }
"PASS: $($docPaths.Count) Markdown files; $linkCount local links resolve; no trailing whitespace; 26 unique acceptance cases."
