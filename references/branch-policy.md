# Branch policy

`main` contains production. `staging` contains testing changes. Dedicated branches begin at fetched staging: `feat/`, `bugfix/`, `docs/`, `chore/` plus a lowercase hyphenated description. Hotfixes begin at fetched main using `hotfix/`. Release names are `release/vX.Y.Z`, optionally with a valid prerelease suffix. No permanent dev branch.

Ordinary task PRs target staging. Same-repository release and hotfix PRs alone may target main. Dedicated chore branches may synchronize into active release branches. All shared branch updates use PRs and merge commits; no direct pushes, force-pushes, or history rewrites. Creating a missing staging ref from main during authorized bootstrap is initialization, not a change merge.

`assets/rulesets/branches.json` protects main, staging, and release branches with reviews, code owner review, stale-review dismissal, last-push review, required conversation resolution, strict required checks, and deletion/force-push prevention. The required status comes from trusted base code, not PR-head scripts. GitHub Actions app ID 15368 is for GitHub.com; verify before adapting to enterprise. Review the ruleset payload and its actual applicability before applying.

Set `.github/CODEOWNERS` to real authorized users/teams. At minimum protect `.github/**`, including CODEOWNERS itself, all controller scripts, workflows, and configuration. A code owner must independently inspect changes to the safety mechanism. Verify reviewer access; a file that names an inaccessible team is not protection. No bypass actors are configured.

Version tag rules prohibit updates and deletion. They allow initial creation for the release job. Administrators must restrict unrelated tag creators through organization policy if needed; immutable tags alone are not proof of a Guardian release. Production also verifies the merged PR, candidate evidence, and tag target.

Use host-native worktree management when required by your agent. The CLI can create a separate Git worktree for tools without such a facility. Never reuse an active branch in two worktrees. Check dirty files before switching; the guardian does not stash or discard other work.
