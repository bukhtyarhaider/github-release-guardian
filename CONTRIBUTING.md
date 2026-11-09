# Contributing to GitHub Release Guardian

Tell us the outcome you want in an issue, or ask your AI coding agent to help prepare a change. Read [the README](README.md) first. For security vulnerabilities, use [private reporting](SECURITY.md), not a public issue.

Start a dedicated feat/, bugfix/, docs/, or chore/ branch from staging. Submit ordinary changes into staging. Only release/vX.Y.Z and hotfix/ branches may request a production merge into main. All shared updates use reviewed pull requests and merge commits. Keep changes focused and preserve the user's existing authorization and work.

Before submitting:

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q scripts tests .github
python3 -m pip install -r requirements-dev.txt
python3 scripts/validate_package.py
```

Run `python3 scripts/package.py` when changing installable files and try the extracted package in a temporary project. Do not point tests at production repositories or cloud accounts. Test runtime changes with Python 3.11 and a current supported Python version. Runtime and unit tests use the standard library; package validation uses the pinned development dependency.

Use a descriptive Conventional Commit title such as `fix: preserve an interrupted release` or `feat: support another provider`. Mark breaking changes explicitly. `release:major`, `release:minor`, `release:patch`, and `release:none` labels explain version impact. Do not label an actual feature or fix as none.

Fill every pull request handoff section with evidence. Tests describe what actually ran; local simulation is different from a successful live deployment. Include migration and rollback implications for behavior or configuration changes. Ask for an independent reviewer; GitHub does not allow authors to approve their own PRs. Dependency bots may need a maintainer to supply handoff details and a compliant branch before their updates can merge.

Code owners must review workflow, permission, configuration, and controller changes. Do not add privileged execution of PR code, expose credentials, loosen approval gates, force-push shared history, or move published version tags. Report partial failures honestly.

See [the maintainer workflow](docs/repository-maintenance.md) for this repository's package candidates and protected releases.
