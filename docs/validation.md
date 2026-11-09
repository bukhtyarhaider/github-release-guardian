# Validation performed

Local verification on 2026-11-09:

- **81 unique automated tests passed** using Python's standard-library unittest runner. Coverage includes valid/invalid branch routing, forbidden feature-to-production requests, release and hotfix paths, SemVer and breaking changes, ambiguous metadata, duplicate versions, missing credentials/permissions, missing staging, failed checks, approvals, candidate drift, hotfix synchronization, divergence, real merge conflicts, archive tampering/traversal/links, and interrupted release recovery.
- Real temporary Git repositories exercised task creation, selected-file commits, refusing direct production saves, leaving an unrelated .env file unsaved, and conflict inspection without modifying the working tree or shared branch refs.
- Installer checks exercised canonical skill and aliases, invoking an installed controller, updates, modified-file refusal, preserving unowned additions, and uninstalling owned files only. Project setup was repeated successfully in a temporary Git project and its copied controller invoked there.
- A static-site fixture actually ran its test/build commands, produced a bundle, and passed extraction and SHA-256/commit/run/repository validation. GitHub and AWS mutation paths use simulated responses; no cloud credentials were used.
- A simulated failure after tag/draft-release creation resumed the same release, published only after a successful deployment response, and avoided deploying an already published release again.
- **Actionlint v1.7.12 passed** all four generated workflows and this package's test workflow. The official binary was downloaded to a temporary directory and its published archive checksum verified. Shellcheck was disabled because it is not installed; Actionlint still validated workflow syntax, contexts, expressions, and action inputs.
- YAML/JSON parsing, internal documentation links, pinned action references, privileged checkout boundaries, Python compilation, and the bundled skill-creator frontmatter validator passed.

Reproduce the local checks:

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q scripts tests
python3 -m pip install -r requirements-dev.txt
python3 scripts/validate_package.py
# If installed:
actionlint -shellcheck= assets/workflows/*.yml .github/workflows/*.yml
```

The runtime controller and unit tests have no external Python dependencies. PyYAML is used only for development package checks. Build a distributable with `python3 scripts/package.py`; its checksum is written beside the ZIP.

## Not verified here

This workspace began as an empty non-Git folder with no target repository or provider configuration. No repository was created, pushed, merged, or reconfigured. No GitHub ruleset/environment was applied; no real GitHub Actions candidate or production run happened; no AWS role, bucket, DNS, CDN, or live site was changed. Agent installation paths were checked against official documentation, but discovery has not been exercised inside separate running Codex, Claude, and Antigravity installations.

A repository administrator must review and apply protections, verify actual code owner access, and inspect any hidden bypass permissions. GitHub omits bypass actor lists from tokens without ruleset write access; the audit reports those lists as unknown rather than claiming they are empty. Ordinary workflow tokens remain subject to the effective server rules. The environment bypass flag must be exposed as false by the target API; if absent or true, production readiness fails closed and an administrator must inspect it.

Before production use, complete the README checklist, run an authorized live staging rehearsal with real application tests and acceptance checks, and exercise the protected production approval/recovery path on a non-critical site. Other hosting providers require their own reviewed adapter and live verification. Local test success is not a certification of a live production account.
