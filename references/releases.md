# Release procedure and recovery state

The release controller is a plan-first interface. The agent can perform all authorized steps without repeatedly asking permission; GitHub still controls independent approvals.

1. `release` verifies access, effective branch protections, production approval configuration, production ancestry in staging and open release PRs, and a successful latest staging candidate run with a nonexpired artifact and successful exact-SHA staging deployment.
2. It enumerates changes since the latest stable production tag, calculates a version, generates categorized notes with real change links, and checks for an existing open production candidate.
3. `release --apply` creates the remote version branch atomically at the approved staging SHA, records local recovery state in the common Git directory, and creates or reuses a release PR. No production branch is pushed directly. The version branch is the cross-machine reservation for that version. Concurrent different candidates with the same version fail the ref creation rather than overwrite it. Maintain one open production candidate; production deployment is serialized independently.
4. Preparation explicitly dispatches another Guardian candidate run on the new branch; a push trigger is also supported. The code is frozen at a SHA, tested, packaged, and deployed to staging. Content changes require fresh evidence; release branches accept synchronization PRs, never direct updates.
5. Trusted policy runs at PR events and candidate completion, checking live evidence on the exact head. `resume --pr N` also collects current reviews, conflict state, protections, artifact identity, synchronization, and ancestry. `resume --pr N --merge` requests a normal GitHub merge with an expected-head-SHA guard. GitHub's required checks remain authoritative.
6. The closed/merged PR event normally requests Guardian production automatically. `resume --pr N --deploy` explicitly dispatches it, which also works when a workflow token suppressed the merge event. The production environment requires its own approval. The agent monitors the actual run and never equates dispatch with success.
7. The protected production job verifies main is still this exact merge commit and that its tree equals the tested candidate tree. It selects the successful same-repository push or explicit-dispatch run and immutable artifact by ID, verifies repository, run ID, candidate SHA, and archive digest, creates an immutable tag and draft release, and deploys the same files. No production rebuild happens.
8. The job verifies home-page and version-marker health, uploads deployment.json with candidate/build/production identities and health result, publishes the draft release, and creates synchronization PRs. A failure after publication is reported as partial success (for example synchronization still pending); rerun sync to recover.

## Interruption behavior

Local writes are atomic and the OS operation lock releases after process exit. A branch-created/pr-not-created interruption can be retried with `release --apply` while that candidate remains current. If staging moved, locate the reserved branch using GitHub and create its PR without changing the branch, or close the abandoned candidate through a reviewed decision. Never silently repoint it.

The local recovery file is a convenience, not authority. Recover on another machine with `resume --pr N`. It reads the current remote PR and evidence. A merged PR can be resumed without local state. A duplicate deployment of an already published matching release is a no-op; synchronization remains recoverable with sync. A draft release with a matching PR and candidate resumes the same version. Tags cannot be moved. If the public site changed but a later step failed, report that partial state accurately and inspect the provider before retrying.

## Rollback

Do not reset main or move a version tag. Prefer a reviewed hotfix/revert with a new version so code and deployment history remain aligned. For an outage requiring restoring an old artifact, obtain explicit incident authorization, select a known verified deployment.json and retained artifact, validate its digest, run a protected provider rollback, verify health, and record the incident/deployment. Then reconcile main and staging through reviewed changes. This package does not silently automate a destructive rollback or database reversal; migration-specific procedures belong in the PR handoff.

## Changelog

Generated release notes group actual change metadata under What's new, What's fixed, Improvements, Important notes, and Technical details when relevant. The GitHub Release is the immutable version's changelog entry; there is no unreviewed CHANGELOG.md push to main. Edit unclear user-facing wording during PR review without inventing changes or tests. Deployment records and candidate run links provide verification evidence.
