# Maintaining this skill repository

This repository's product is an installable **skill ZIP**, distributed through GitHub Releases. Its staging environment verifies package checksums, extraction, installation, and the installed help command. There is no website or cloud infrastructure to provision for the package itself. AWS/static-site workflows in assets/workflows are examples for downstream applications, and are not activated here.

## Everyday changes

Start a feat/, bugfix/, docs/, or chore/ branch from staging. Complete the PR handoff, run the relevant local checks, and submit into staging. Required package tests exercise Python 3.11 and 3.13. A separate trusted policy status validates branch routing and the handoff without executing PR-head code. Independent owner review and merge commits preserve traceability.

When approved work reaches staging, Package candidate tests the source, builds the ZIP once, records source SHA/repository/run/version/SHA-256 in candidate.json, and uploads the ZIP and checksum as an immutable workflow artifact. The staging job downloads those exact files and verifies installation without passing GitHub or cloud credentials into the package subprocess. A successful GitHub staging deployment records that verification. It does not mean a downstream application's website or production account was tested.

Dependabot proposes weekly Action and Python dependency updates into staging. The trusted policy recognizes only same-repository PRs authenticated as dependabot[bot], maps their names to maintenance intent, and supplies a bounded generated handoff for validation. It never trusts a user-provided “I am a bot” claim. Required tests and independent review still apply. Maintainers should document unusual compatibility implications in the PR before merging.

## Prepare a release

1. Inspect changes since the previous stable tag and use the canonical version calculator to choose their highest impact. The initial package version is 1.0.0; do not call a later change 1.0.0 after it has been published.
2. Update scripts/guardian/__init__.py on a normal maintenance branch, submit into staging, and wait for current package tests and candidate verification. Record breaking changes and migrations in the relevant handoff.
3. Create release/vX.Y.Z at the approved staging SHA. Dispatch Package candidate on that branch when needed; evidence must match its exact head. Do not add untested edits to a frozen candidate.
4. Open a release PR into main with the full handoff, actual change notes, candidate run link, and required independent review. Repository policy permits only release/ and hotfix/ PRs to target main. The candidate must include current main, and staging must retain all production fixes.
5. Merge using the normal approved GitHub process. Publish verified package requests production-environment approval. It verifies the exact merge parents/tree, candidate run and artifact identity, built version, and checksum; then it installs the downloaded package in an isolated temporary directory. It creates a tag/draft release, uploads that same ZIP plus checksum and deployment.json, and publishes. It never rebuilds for production.
6. Follow the actual job to completion. A merged PR or accepted dispatch is not release success. Check the published release assets and production deployment record. Ask the authorized agent to prepare synchronization PRs from current main into staging and other open release branches, review/merge them, and verify ancestry. Workflow tokens do not need permission to approve PRs.

Use `workflow_dispatch` with the merged PR number to resume after an interrupted publication. The exact matching draft release is reused. A matching published release is a no-op; a version owned by another candidate is blocked. Published release immutability and tag protection prohibit changing historical assets or tags. A failed upload may leave a reserved tag or draft release; inspect remote state before retrying and never move the tag.

Hotfixes begin at current main, change the package to the next stable patch version, pass the same candidate and review gates, and target main. Synchronize production back into testing afterward. Urgency does not permit self-approval or bypass.

## Review and approval

The owner is the default code owner. Another authorized GitHub account must independently review owner-authored work. Production deployments must also have a required reviewer, prevent self-review, and disallow administrator bypass. If no reviewer has been chosen, releases remain locked. Never temporarily remove a protection to make a test or release pass.

No Actions secrets or external provider credentials are needed for this package workflow. Default workflow permissions stay read-only; the policy job can post its status, and only the production job receives contents write after its environment gate. No workflow is granted permission to approve its own PRs.

## Repository setup and changes

The initial repository setup uses one reviewed bootstrap PR because its policy workflow must exist on the trusted default branch before GitHub can use it. Activate required checks and protections only after that PR's CI has passed and it is merged; then create staging from the resulting main commit and validate a real package candidate. All later work follows the enforced branch architecture.

Repository-wide settings, label definitions, ownership, and live verification evidence are recorded in [repository setup](repository-setup.md). That record describes observed configuration, not permission to change it.
