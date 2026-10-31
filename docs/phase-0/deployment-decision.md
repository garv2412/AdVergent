# Deployment decision and prerequisite evidence

Date: 2026-10-27. Scope: Phase 0 research and read-only inspection; no provisioning or installations.

## Decision

Prefer AWS under the existing Free account plan, without upgrading the account. Keep local Exasol Personal as the accepted fallback. Cloud deployment is conditional on the Phase 1 preflight below, not certified operational by this document.

Phase 0's planning gate is satisfied by a documented supported route, fallback, prerequisites, and explicit unresolved checks. Installation, actual instance eligibility/quota checks, connectivity, bulk loading, and `SELECT 1` are Phase 1 execution gates. This clarifies the earlier ambiguous phrase "runtime feasibility pending"; it does not claim runtime verification.

## Account evidence

The user supplied console text on October 27:

- Remaining credits: USD 139.73.
- Displayed remaining duration: 101 days.
- Displayed free-access end date: February 3, 2027, or credit exhaustion, whichever occurs first.
- Console offers an upgrade for uninterrupted access.

This wording is consistent with AWS's Free account plan. It is user-supplied console evidence, not an authenticated API inspection. Record the displayed duration and date as supplied; do not infer a new expiration or a separate credit expiry from the counter. Reconfirm current balance/plan before provisioning because other workloads may consume credits.

AWS documentation states that its Free plan does not incur charges and closes when its duration/credits end; the Paid plan can charge beyond credits. Do not upgrade, join an Organization, configure Control Tower, or take other actions that automatically convert the plan. Budget alerts supplement monitoring; they do not enforce a spending cap.

## Exasol version and AWS compatibility findings

GitHub's latest-release API returned **v2.3.0**, published September 21, 2026. Its versioned system requirements document Ubuntu 24.04 x86-64 cloud deployment and Windows AMD64 local deployment through Podman. Pin/reconfirm the release and official binary integrity during Phase 1 rather than installing from an unreviewed moving branch.

The v2.3.0 AWS preset defaults to one `r6i.xlarge`, 100 GB root storage, 100 GB data storage, and enabled S3 archive integration. AWS's published Free-plan EC2 list instead includes `t3.micro`, `t3.small`, `t4g.micro`, `t4g.small`, `c7i-flex.large`, and `m7i-flex.large`.

Therefore **do not run the AWS installer with unchecked defaults**. A configurable x86-64 instance such as `m7i-flex.large` is a candidate, not a verified Exasol sizing recommendation. Confirm actual launcher/database resource requirements, region availability, account quota, and storage eligibility first. Do not substitute an ARM instance without explicit database/preset support.

Preferred region: `ap-south-1` (Mumbai), subject to actual availability; the region in a billing URL is not proof of EC2 availability. No instance, storage size, or cost estimate is approved as validated yet. Evaluate complete resource consumption, including storage, public IPv4, transfer, archive/bootstrap buckets, and support resources, against the remaining credit balance.

## Local fallback evidence

Read-only inspection found:

| Item | Result |
|---|---|
| Host | Windows 11 Home, 64-bit |
| Physical RAM | Approximately 15.8 GiB |
| D: free disk | Approximately 128.5 GiB at inspection |
| WSL | Version 2 default; default distribution is docker-desktop |
| Docker CLI | 29.6.2; Linux engine unavailable during inspection |
| Windows Package Manager | `winget` available |
| Podman | Not found in PATH |
| AWS CLI / Exasol launcher | Not found in PATH |
| Node / Python | Executables found; versions and dependency compatibility not checked |

Docker availability does not establish the Podman prerequisites required by Exasol's Windows local route. No application Linux distribution was established by this inspection. Podman-machine preparation and sufficient usable memory/storage remain Phase 1 tasks. Do not substitute Community Edition for the requested Personal edition without discussion.

## Phase 1 preflight and stop conditions

1. Reconfirm AWS Free-plan status and current credits through a user-authenticated method. Configure supported credentials outside repository/chat; do not create or print long-lived keys in logs.
2. Inspect eligible instance offerings, quotas, AMI architecture, and applicable service restrictions in Mumbai. Read-only checks precede any resource creation.
3. Review the pinned Exasol preset's resource plan, network rules, storage sizes, and full credit consumption estimate. Preserve the Free plan. Restrict database/admin access; never use broad public database ingress.
4. If a compatible AWS configuration is not available without upgrading, choose local Exasol. Validate/install the required Podman environment and pinned launcher during Phase 1.
5. For local Exasol plus cloud application, validate a secure application-level connection and available uptime; do not expose the database publicly. If this topology fails, ask about a local whole-application fallback, which is not yet accepted.
6. Prove TLS/authentication, `SELECT 1`, golden-fixture loading, analytical query, and failure reporting before calling the foundation operational.
7. Inventory and tag resources, preserve deployment state securely outside Git, and plan cleanup. Stopping compute does not remove storage or other credit consumption. Interrupted provisioning may leave resources behind.

## Schedule implication

Phase 0 closes on October 27 rather than the original October 26 target. Phase 1 starts in a separate chat. Proposed remaining demo sequence: October 27 foundation/runtime gate; October 28 source fixtures, finance/inventory, approved simulated execution; October 29 predictive/diagnostic baselines; October 30 integration of included modules, regression, deployment, and rehearsal by 23:59 IST.

These are compressed targets across the original phase numbers, not a guarantee or authorization to merge phases/chats. Each implementation chat must estimate its bounded scope and report slippage. The full production roadmap remains deferred; no acceptance case is waived automatically.

## Commands and sources checked

Read-only local commands: `Get-Command aws,docker,wsl,exasol,node,python -ErrorAction SilentlyContinue`, `Get-Command winget,podman -ErrorAction SilentlyContinue`, `Get-CimInstance Win32_ComputerSystem`, `Get-CimInstance Win32_OperatingSystem`, `Get-PSDrive D`, `docker version --format '{{.Client.Version}} / {{if .Server}}{{.Server.Version}}{{end}}'`, and `wsl --status`. Docker's daemon probe failed; that failure is recorded, not repaired. Sources were fetched without saving/installing external code.

- AWS account-plan rules: https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-plans.html
- AWS Free-plan EC2 eligibility: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-free-tier-usage.html
- AWS budget update/notification limitations: https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html
- Exasol latest release API: https://api.github.com/repos/exasol/exasol-personal/releases/latest
- Versioned runtime requirements: https://github.com/exasol/exasol-personal/blob/v2.3.0/user-docs/content/system-requirements.md
- Versioned local guide: https://github.com/exasol/exasol-personal/blob/v2.3.0/user-docs/content/local-deployment.md
- Versioned AWS variables: https://github.com/exasol/exasol-personal/blob/v2.3.0/assets/infrastructure/aws/variables_public.tf

Some indexed Exasol quick-start results describe older macOS-only local requirements. Versioned v2.3.0 source documentation was used to resolve this discrepancy. Windows deployment itself has not been tested here.
