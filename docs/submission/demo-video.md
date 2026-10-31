# Demo video

**Recording URL: pending.** This document is a recording guide, not a demonstration video. The repository cannot yet support a confirmation that all submission materials, including a demo video link, are present.

Supply an accessible recording URL and add it to the README submission table and [submission description](../hackathon-submission.md). Verify that judges can open it without requesting access. Confirm the event's required format and maximum duration.

## Suggested recording sequence

The timings below form a proposed five-minute outline, not an official event requirement.

| Approximate time | Screen and narration |
| --- | --- |
| 0:00–0:35 | Explain the apparel merchant problem and Track 02 fit. Revenue alone can hide returns, missing costs and stock constraints. |
| 0:35–1:05 | Show the authenticated application, synthetic-data labels and real Exasol foundation calculation: INR 4,000 sales and INR 300 contribution after ads. |
| 1:05–1:55 | Show commerce, channel attribution and financial cost coverage. Explain that unknown costs remain unknown. |
| 1:55–2:40 | Show inventory cover/size availability and sparse demand signals. Explain historical freshness and abstention. |
| 2:40–3:20 | Show customer cohorts, separate maturity windows and incomplete-history coverage. |
| 3:20–4:15 | Query budget and unified decisions. Explain INR 11,000/day fixed total, frozen default budgets and inventory precedence. |
| 4:15–5:00 | Show architecture and public source/setup links. State the synthetic local scope and remaining gaps. |

Use [the pitch deck](AdVergent-pitch-deck.pptx) for the problem, architecture and closing slides. Use the working application for the demonstration itself. Do not record passwords, tokens, private configuration, launcher credentials or sensitive browser content.

The recording should inspect existing state only. Do not create approvals, execute advertising changes, reset/delete history or deliberately stop services for the recording. Existing failure/recovery evidence is documented in [the runbook](../phase-14-demo.md) and must retain its actual verification status.

## Suggested opening narration

“AdVergent addresses Track 02, Customers, Channels & Demand. Apparel merchants see advertising revenue, customer orders and warehouse stock in separate systems. A campaign can look successful even when returns or missing sizes make more spending unsafe. Our local prototype uses real Exasol Personal SQL to bring synthetic commerce and channel evidence into one decision workspace.”

## Suggested closing narration

“The prototype shows customer cohorts, channel contribution and demand signals with inventory protection. It exposes uncertainty and abstains when evidence is insufficient. The analytics use real Exasol Personal, the business records are synthetic, and advertising actions are simulated with explicit approval. The repository includes source, a pitch deck and setup instructions. Live integrations and production effectiveness remain future validation work.”
