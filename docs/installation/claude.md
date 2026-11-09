# Install for Claude Code

This package is one canonical Agent Skill, plus optional thin aliases. From the downloaded package directory, install into a **different target project**:

```sh
python3 scripts/install.py --agent claude --scope project --project /absolute/path/to/project
```

For all of your projects:

```sh
python3 scripts/install.py --agent claude --scope user
```

Project destination: `.claude/skills/github-release-guardian`. User destination: `~/.claude/skills/github-release-guardian`. The installer copies the canonical skill, scripts, references, and assets; it does not change agent permissions or repository settings. [Official Claude Code documentation](https://code.claude.com/docs/en/skills).

## Invoke and verify

Use `/github-release-guardian` followed by your request, or natural language. Add `--aliases` during installation for `/github-setup`, `/github-status`, `/github-start`, `/github-save`, `/github-submit`, `/github-test`, `/github-release`, `/github-hotfix`, `/github-sync`, and `/github-help`. These are thin skill adapters, with all business logic in the canonical skill.

Ask “Inspect my GitHub setup without changing anything.” Verify it reads this SKILL.md and runs the audit from the target project. Connect GitHub using an existing authorized integration or secure `gh auth login` in the environment running the scripts. Never paste credentials into a prompt. A hosted agent may need its own CLI authorization; local user installation does not automatically transfer to every cloud session.

The agent must report missing GitHub access honestly. Installing a skill does not grant tool execution or production permissions. Review the [prerequisites](../../references/prerequisites.md).

## Update or remove

Run the installer from a reviewed newer package using the same agent/scope/project arguments plus `--update`. Include `--aliases` on an update if you want aliases retained. Updating without it removes previously owned alias files. The installer checks its manifest and refuses to overwrite modified installed files or unowned files. Preserve and merge local modifications first.

Use the same arguments plus `--uninstall` to remove only installer-owned, unchanged files. Files you added are retained. Uninstalling the skill does not remove GitHub protections, project workflows, environments, releases, or hosted sites. Disabling those requires a separate reviewed migration.
