# Verified GitHub repository setup

Repository: [bukhtyarhaider/github-release-guardian](https://github.com/bukhtyarhaider/github-release-guardian).

Verified on 2026-11-09. [Bootstrap PR #1](https://github.com/bukhtyarhaider/github-release-guardian/pull/1) passed its GitHub checks and was merged using a merge commit. Main and staging were initialized at production commit `2de07a94e1c7422b27a4b96d1f8bc68db24068cd`.

## Active repository configuration

- Public repository, descriptive About text, README website link, and eight relevant topics.
- Merge commits enabled; squash and rebase merging disabled. Suggested branch updates enabled. Published-release immutability enabled.
- [Guardian repository branches](https://github.com/bukhtyarhaider/github-release-guardian/rules/26862079) actively protects main, staging, and release/**. It requires a PR, one independent approval, code owner review, dismissal of stale approvals, approval of the latest push, conversation resolution, up-to-date branches, and `repository-policy` plus `package-tests` from GitHub Actions. Force pushes and deletion are blocked. The bypass list is empty; the API reports the current user can never bypass this ruleset.
- [Guardian repository version tags](https://github.com/bukhtyarhaider/github-release-guardian/rules/26862321) actively prevents changing or deleting v* tags. Published release assets are also immutable.
- Eight additional labels cover release:major/minor/patch/none, dependencies, needs-triage, blocked, and breaking changes. The repository retains its original issue labels.
- Community guidance, private security reporting instructions, issue forms, a full PR handoff template, code ownership, weekly dependency updates, and maintainer/agent guidance are on main.
- Actions default to read-only contents/packages access. GitHub Actions cannot create or approve PRs. External contributor workflow runs require approval. Only owner-local or GitHub-authored actions are allowed, with full commit SHA pinning required. Artifact/log retention is 90 days.
- Private vulnerability reporting, dependency graph, Dependabot vulnerability and malware alerts, and Dependabot security updates are enabled. Secret scanning and push protection remain enabled. CodeQL default setup scans Python and GitHub Actions; no paid agentic scans were enabled.

The repository-specific imported branch/tag payloads are preserved under `.github/rulesets/`. The templates under assets/rulesets are for downstream application repositories and use different required check names.

## Verified live workflows

- [Bootstrap PR checks](https://github.com/bukhtyarhaider/github-release-guardian/actions/runs/42592751922) passed, including the Python 3.11/3.13 matrix and aggregate required check.
- [Main checks](https://github.com/bukhtyarhaider/github-release-guardian/actions/runs/42592890738) passed after the merge.
- [Staging checks](https://github.com/bukhtyarhaider/github-release-guardian/actions/runs/42592960140) passed.
- [Package candidate and staging verification](https://github.com/bukhtyarhaider/github-release-guardian/actions/runs/42592960162) passed: the ZIP was built once, recorded with source/run/version/checksum provenance, then downloaded, verified, installed in isolation, and smoke-checked in the staging environment.
- [CodeQL setup and initial analysis](https://github.com/bukhtyarhaider/github-release-guardian/actions/runs/42665431766) passed.
- 90 local tests, package YAML/JSON/link checks, Python compilation, and Actionlint passed during setup.

Staging only permits the staging, release/*, and hotfix/* branches; administrator bypass is disabled. This environment validates the **skill package**, not a hosted downstream application. No AWS or other cloud account is required for this repository's ZIP releases.

## Production is deliberately locked

There are currently zero collaborators and no independent reviewer has been selected. GitHub does not permit an author to approve their own PR. Production exists with administrator bypass disabled and a selected branch rule named `guardian-production-locked`, which matches no branch. The release workflow itself only executes on main, so this environment cannot currently publish a package. The publication helper independently rejects missing required reviewers and non-main production branch policies.

To activate releases, the owner must choose and authorize an independent GitHub reviewer, establish their access and code ownership through the approved process, configure required production review with self-review prevention, and replace the deliberate lock rule with an exact main-only branch policy. Do not weaken or bypass reviews to make an owner-authored change pass. An automatic approval review rejected using the owner as the missing independent production reviewer; no such reviewer was configured.

No release or version tag was published by setup. Production publication and recovery still need an authorized live rehearsal after the independent review gate is configured. The local GitHub CLI credential remains invalid; the connected GitHub integration and verified browser session were used for setup. Runner workflows use GitHub's scoped job token and do not depend on that local credential.

Read [the maintainer workflow](repository-maintenance.md) for operating and recovery procedures. This document records observed setup, not permission to modify it.
