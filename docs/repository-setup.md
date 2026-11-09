# GitHub repository setup

Repository: [bukhtyarhaider/github-release-guardian](https://github.com/bukhtyarhaider/github-release-guardian).

The initial four commits were uploaded to a public main branch. GitHub's first [Package tests run](https://github.com/bukhtyarhaider/github-release-guardian/actions/runs/42590177183) completed successfully on commit c2bdbcc148f26f387d2295701a956bec7e21ed70.

This setup change adds repository-specific package validation, staging verification and protected GitHub Release publication, community files, issue/PR forms, dependency updates, code ownership, and maintainer/agent instructions. The ZIP publication path needs no AWS credentials or hosted application.

Repository settings being applied include merge commits, immutable published releases, descriptive metadata, required checks and reviews, protected branch/tag rules, and separate staging/production environments. Settings must be checked against the live GitHub UI/API; files alone do not activate protections.

At preparation time, the local GitHub CLI credential is invalid. The connected GitHub integration can manage code/PRs, and the browser is signed in, but GitHub asks the owner to confirm access for protected settings. An independent reviewer has not yet been selected. Production must remain locked until a valid reviewer and the required environment protection are in place. No release has been published by this setup operation.

This record will be updated with actual bootstrap PR, workflow, and protection evidence after configuration. Read [the maintainer workflow](repository-maintenance.md) for operating procedures and [security limitations](security.md) for the trust boundary.

The setup change passes 90 local tests, Python compilation, package JSON/YAML/link checks, and Actionlint. The repository description, README link, eight topics, deployment visibility, and eight release/triage/dependency labels have been saved in GitHub. Merge commits are enabled; squash/rebase merging is disabled, update-branch suggestions are enabled, and published-release immutability is enabled. Remaining protected settings require live verification before this record claims they are active.
