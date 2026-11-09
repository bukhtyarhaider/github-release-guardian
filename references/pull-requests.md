# Review requests

Use a separate task branch and review the full diff before saving or pushing. Ordinary work targets staging; only approved production candidates and urgent fixes target main. The submit command updates an existing matching open PR instead of creating duplicates.

Fill every section in `assets/pull_request_template.md`. Comments are prompts, not completed handoffs. Record the reason, actual behavior, important files, tradeoffs, exact tests and outcomes, Ready/Needs attention/Blocked status, remaining work, known problems, links, and next steps. Use “None known” when appropriate; do not invent results.

Use a Conventional Commit PR title such as `feat: add Google login` or `fix: repair checkout`. Labels `release:major`, `release:minor`, `release:patch`, and `release:none` provide explicit metadata. Breaking changes always win. Include end-user wording in the title because release notes derive their claims from actual metadata.

Guardian CI runs the PR merge content with a read-only token, no environment, no cloud credentials, and no checkout credentials persisted. The privileged source-policy evaluator checks out the trusted base only and never executes PR-head code. Do not add PR-driven script execution, artifact execution, or unsafe shell interpolation to that workflow.

GitHub approvals and branch protections decide whether a merge is allowed. The agent may request approval but cannot approve its own change, impersonate another reviewer, or use an administrator bypass. Use merge commits. After a staging merge, wait for its candidate deployment and inspect health.
