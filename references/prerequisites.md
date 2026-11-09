# Access and prerequisites

Use Python 3.11+, Git 2.38+ (for non-mutating merge conflict inspection), and GitHub CLI. GitHub.com is the supported API target; GHES requires adapting the Actions app integration ID, artifact actions, and plan capabilities.

Inspect `git --version`, `python3 --version`, `gh --version`, and `gh auth status`. Do not print tokens, credential-bearing remotes, `.env` values, environment variable values from GitHub, or cloud credentials. The audit reports secret and variable names only. Unknown permissions are reported as unknown, never interpreted as an empty configuration.

Prefer an already connected GitHub integration for read and write operations if it has the needed capabilities. Executable automation uses `gh`, so a connected app alone does not guarantee CLI access. Run `gh auth login` locally if needed. Fine-grained access should be limited to the selected repository: metadata read, contents/PRs write for task operations; actions/deployments read and actions write for dispatch; administration write only for explicitly approved setup; environments write only where required. Workflow file pushes may require additional workflow authorization depending on token type. Organization SSO may require authorization.

Do not automatically upgrade plans. Ask an administrator to check unavailable required protections. A lone reviewer cannot review their own changes or approve their own triggered production job; use a separate authorized reviewer. Local work can continue when deployment access is blocked.

New repositories need an initial production commit before Guardian can branch from it. Migrating another default branch to main requires a separately reviewed migration, including existing integrations and default-branch settings. Guardian does not silently rename it.
