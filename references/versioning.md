# Version decisions

Semantic Versioning uses major.minor.patch: breaking behavior, compatible features, compatible fixes. A release number describes the changes, not the number of commits.

Priority for each change:

1. A `BREAKING CHANGE:` / `BREAKING-CHANGE:` declaration, Conventional Commit `!`, explicit breaking flag, or `release:major` label always means major.
2. Otherwise take the highest explicit release label among minor and patch. A release:none label conflicting with a recognized feature/fix or another release label blocks and asks a simple question.
3. Otherwise Conventional Commits infer feat → minor, fix/perf → patch; docs/chore/test/ci/build/style/refactor/revert → none. Unknown commit types or unstructured messages block instead of guessing.
4. Take the highest impact across the release. No-impact-only changes do not automatically produce a release. Explicitly label a change if a release is intended.

Merged staging PR titles, bodies, and labels are preferred to raw commits; multiple commits in one PR are deduplicated. Non-merge commits without a merged staging PR must classify independently. Breaking declarations are never silently downgraded by a lesser label. A plain revert is not presumed to be a bug fix; an explicit label can classify its user impact.

Choose the highest stable version tag reachable from main using numeric SemVer ordering. Non-semver history without a stable baseline requires an explicit baseline_ref and initial_version; never silently rename existing versions. With no version history, changes after current production are released at configured initial_version (default v0.1.0). The initial production commit itself is not a new change.

Before an initial prerelease with no stable history, record the original production SHA as baseline_ref so later stable promotion retains the same changes. `release --prerelease rc` generates `vX.Y.Z-rc.1` and increments existing channel numbers. Prereleases use the production release path and approval gate; do not treat the label as permission to deploy an untested build. A stable release of the same base version is calculated against the last stable tag. The pure version helper also supports promoting an explicitly provided prerelease current version to its stable number. Build metadata is intentionally not used for version tags.

If a tag already exists, block a new release at that version; resume the existing release. Hotfixes calculate a patch version from stable production tags reachable from the first parent of their merge commit, making retries deterministic.

Offline helper input example:

```json
{"current":"v1.4.2","changes":[{"message":"feat: add Google login","labels":[]}],"existing":["v1.4.2"]}
```

`python3 scripts/calculate_version.py --input changes.json` returns v1.5.0. This helper does not verify live release readiness.
