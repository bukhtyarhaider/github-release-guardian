# Recovery reference

| Situation | Safe next step |
| --- | --- |
| GitHub credentials missing | Run gh auth status locally, then gh auth login; never send a token in chat. |
| Missing permissions or ruleset access | Ask an administrator to check repository role, SSO, plan, and effective rules. Unknown is not success. |
| Unsaved work | Review the diff and save selected files on the current task; do not stash/discard automatically. |
| Automatic checks failed | Open the failed job, identify the actual error, fix on a dedicated branch, retest. |
| No testing deployment | Complete provider isolation and OIDC setup; run a real candidate deployment. Production stays blocked. |
| Missing review | Request an authorized independent reviewer. Never approve as the author or bypass. |
| Candidate changed or production advanced | Synchronize through PRs, then run fresh candidate validation and request fresh reviews. |
| Artifact expired | Re-run candidate validation. Do not rebuild an unrelated commit for production. |
| Version already reserved | Inspect the existing branch/tag/release and resume its PR instead of overwriting it. |
| Process interrupted before a PR existed | Inspect reserved release branch and current staging; retry only if the candidate matches. |
| Process interrupted after merge | Resume with the PR number; inspect draft release, tag and deployment records. |
| Site is unhealthy | Keep the release draft, inspect actual hosting/CDN state, then resume the same candidate or authorize a reviewed rollback. |
| Release published, synchronization failed | Report public release success and pending sync separately; run sync --apply and review requests. |
| Installed skill modified | Preserve edits and review them; installer refuses to overwrite or uninstall changed files. |
| Existing workflows conflict with setup | Merge configuration and CI deliberately; local setup overwrites no existing differing files. |

Production dispatch is asynchronous. Use gh run list/view/watch or native GitHub tools to follow it. Stop polling when it needs a human reviewer and provide the exact GitHub link. Resume once approval arrives. Never convert an API timeout into an assumption that a write failed: inspect remote state before retrying.
