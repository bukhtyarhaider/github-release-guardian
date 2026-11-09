# Other agents and manual installation

Start with the guide for [Codex](codex.md), [Claude Code](claude.md), or [Google Antigravity](antigravity.md) when applicable. These include project/user installation, invocation, verification, updates, and removal.

For another Agent Skills-compatible tool, consult its current official documentation for its skill directory. Install with an explicit destination (the directory that will contain github-release-guardian):

```sh
python3 scripts/install.py --agent generic --destination /absolute/path/to/tool/skills
```

The [Agent Skills specification](https://agentskills.io/specification) defines the SKILL.md format; it does not guarantee every agent can run scripts, access GitHub, or approve deployments. Generic installation creates no claimed native slash commands. Use “Read GitHub Release Guardian and inspect my project.”

For a tool without a skills loader, add a short, reviewed pointer to its supported project instruction file: “For GitHub setup, testing, releases, and hotfixes, read /absolute/path/to/github-release-guardian/SKILL.md and use its workflow within the user's authorization.” Do not overwrite existing instructions or invent an instruction filename unsupported by the host. A read-only agent can inspect and explain but cannot complete release mutations.

Connect GitHub through the tool's supported integration or authenticated gh in its execution environment. Run a read-only audit to verify the agent discovered the package and selected the intended target repository. Do not install a global skill into a cloud session and assume it transfers to all machines.

For updates/removal use the same installer arguments with --update or --uninstall. The installer refuses changed owned files, preserves user-added files, and leaves repository hosting/protections untouched. Keep reviewed local modifications before updating.
