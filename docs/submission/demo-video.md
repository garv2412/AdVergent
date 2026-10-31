# Demo video

[Watch or download the MP4](https://raw.githubusercontent.com/garv2412/AdVergent/main/docs/submission/AdVergent-demo.mp4)

Duration: approximately **4 minutes 48 seconds**. Format: H.264 video with AAC audio, 1280 × 840 pixels. The video includes burned-in captions. [Separate subtitles](AdVergent-demo.srt) and [full transcript](demo-transcript.md) are available.

Created October 31, 2026 IST from actual authenticated views of the existing local application and the project pitch deck. This is an edited still-frame walkthrough with synthetic voice narration, rather than a continuous screen recording. All captured analytical endpoints returned HTTP 200. No API response substitutes, source imports, advertising changes, approvals or action execution were used to create the footage. Login/logout used the existing private operator configuration, which is excluded from the recording.

## Production tools and rights

Playwright and installed Chrome captured the application views. Microsoft Windows System.Speech provided the Zira synthetic voice. FFmpeg 7.1 encoded the video/audio and captions, using a local build distributed through imageio-ffmpeg 0.7.0. The wrapper declares BSD-2-Clause; the encoder build reports GPL version 3 or later. Tool binaries and private build files are excluded from Git. No external model API or paid service was used. Project-authored screenshots, slide content, narration text and finished media accompany the repository MIT licence; upstream tools retain their own terms. No music or stock imagery is included.

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
