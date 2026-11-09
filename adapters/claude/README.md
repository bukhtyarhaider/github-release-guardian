# Claude Code adapter

Use [the installation guide](../../docs/installation/claude.md). `scripts/install.py --agent claude` copies the single canonical implementation to the officially documented discovery directory. Use `/github-release-guardian` followed by your request, or natural language. Add `--aliases` during installation for `/github-setup`, `/github-status`, `/github-start`, `/github-save`, `/github-submit`, `/github-test`, `/github-release`, `/github-hotfix`, `/github-sync`, and `/github-help`. These are thin skill adapters, with all business logic in the canonical skill.

The adapter does not grant tools or credentials. Keep the target app's permission controls and GitHub's required reviews. Verify discovery with a read-only audit before authorizing writes.
