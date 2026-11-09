# Engineering guide

## Package and controller

The canonical SKILL.md routes intent to deterministic standard-library Python helpers. `scripts/guardian.py` is the CLI; thin named scripts invoke the same implementation. Local project setup copies controllers and templates into `.github/guardian/`, four workflows into `.github/workflows/`, and issue/PR templates into .github. No Python packages are needed at runtime. Configuration is strict JSON. Optional developer validators have separate dependencies.

Use setup from the installed skill, not a different unreviewed checkout. `setup` lists the exact destination files; `setup --apply` refuses differing existing files before writing any files. Updating an existing deployment requires a reviewed diff/merge, not overwriting custom configuration. `settings` plans remote changes; `settings --apply-settings --reviewer LOGIN --codeowners-verified` authorizes application. Namespaced rulesets coexist with existing settings. Existing production environment policies are not silently replaced; partial remote application is reported and must be inspected before retry.

## Bootstrap order

Inspect the repository, default branch, existing CI, environment isolation, secrets names, and permissions. Establish existing main with a separately reviewed branch migration when necessary. In a new empty repository, an administrator must authorize its initial commit/branch creation; Guardian cannot create a PR against an unborn branch.

Prepare the setup on `chore/guardian-setup` from current production if staging does not exist. Configure real code owners, test/build commands, AWS roles and buckets, and environment restrictions. Submit the initial setup through a GitHub review request before enabling Guardian required checks. Existing repository requirements still apply. This one-time bootstrap is necessary because policy code must already exist on the trusted default branch to check future PRs. Do not directly push setup to production.

After reviewed bootstrap, authorize settings application; missing staging is created from main. Run initial check workflows to register their status names. Verify the effective rules including inherited organization rules, no bypass actors, code owners, and independent production approvals. Merge a small ordinary staging PR and inspect its successful exact-candidate deployment. Until all of this passes, setup is incomplete.

## Useful commands

From the managed project, use the installed controller path:

```sh
python3 /path/to/skill/scripts/guardian.py audit
python3 /path/to/skill/scripts/guardian.py setup
python3 /path/to/skill/scripts/guardian.py setup --apply
python3 /path/to/skill/scripts/guardian.py start 'Add Google login' --apply
python3 /path/to/skill/scripts/guardian.py save --file src/login.py --message 'feat: add Google login' --apply
python3 /path/to/skill/scripts/guardian.py submit --title 'feat: add Google login' --body-file /tmp/handoff.md --apply
python3 /path/to/skill/scripts/guardian.py test
python3 /path/to/skill/scripts/guardian.py release --apply
python3 /path/to/skill/scripts/guardian.py resume --pr 42 --merge --deploy
python3 /path/to/skill/scripts/guardian.py sync --apply
```

The commands above are execution examples, not authorization to change any specific repository. Save/submit/release actions preserve reviews. A release creates no version-file commit and does not rewrite package manifests; applications requiring embedded versions need a reviewed candidate-preparation hook before freezing, then fresh build verification. GitHub Release notes are the versioned changelog.

The local common Git directory holds the release state and process lock shared by worktrees. Remote version refs provide atomic version reservation. Main merges use an expected-head-SHA guard; GitHub enforces required checks. Production jobs use one repository-wide concurrency group. Staging jobs use one group shared by staging/release/hotfix branches. GitHub may replace a pending queued run in a concurrency group: inspect actual candidate evidence and rerun when necessary; never assume every pushed commit deployed.

See [release mechanics](../references/releases.md), [security](security.md), and [validation](validation.md).
