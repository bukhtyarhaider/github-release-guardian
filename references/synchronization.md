# Synchronization without losing work

Use `sync` to inspect main ancestry in staging and branches with open release PRs into main. Completed release branches are not considered active. Staging may contain many unreleased changes and does not need to equal main. The required invariant is that main's history is included, which protects production fixes even when PRs contain merge commits.

`sync --apply` prepares one deterministic chore branch from the current production commit per missing target and creates/reuses a PR into that target. It never merges the request automatically. The PR shows production's changes relative to that target; a normal merge preserves the target's unreleased work. Inspect changed files and GitHub's merge conflict calculation before merging. A squash merge loses the ancestry proof and is disallowed by the supplied rules.

Run `scripts/check_sync.py` again after merging to verify live ancestry. If the main PR's policy status is stale after synchronization, dispatch Guardian policy with its PR number or rerun the evaluator. Production preparation always rechecks live state.

For an outdated local task branch: inspect dirty changes, fetch origin/staging, run `git rev-list --left-right --count HEAD...origin/staging`, and use `git merge-tree --write-tree HEAD origin/staging` for read-only conflict detection. Merge staging only into a dedicated clean task branch under authorization, resolve overlapping changes using the current implementation, run relevant tests, and push normally. No force-push or shared-history rewrite.

Two changes affecting the same part of the project are not automatically an error in either change. Explain the behavior that must be preserved. If resolution affects acceptance criteria or production behavior and cannot be inferred safely, ask a plain-English question while continuing independent work.
