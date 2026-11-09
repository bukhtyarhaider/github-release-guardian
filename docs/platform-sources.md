# Platform sources checked

Checked against official sources on 2026-11-09. These describe supported file formats and installation locations; they do not certify that an uninstalled agent has discovered this package.

- [OpenAI local skills](https://learn.chatgpt.com/docs/build-skills): Codex project/user discovery under .agents/skills; explicit $skill-name invocation; optional agents/openai.yaml metadata.
- [Claude Code skills](https://code.claude.com/docs/en/skills): project/user .claude/skills locations and /skill-name invocation. Thin alias skills route to the canonical implementation.
- [Google Antigravity skills](https://antigravity.google/docs/skills): workspace .agents/skills, global ~/.gemini/config/skills; legacy .agent/skills compatibility.
- [Antigravity workflow migration](https://antigravity.google/docs/migration/workflows-to-skills): skill slash invocation. Natural language remains the portable fallback.
- [Agent Skills specification](https://agentskills.io/specification): canonical folder, YAML frontmatter, and progressive references/resources.
- [GitHub rules API](https://docs.github.com/en/rest/repos/rules): effective branch rules across repository and organization rulesets.
- [GitHub environments](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments): environment approvals and plan limitations.
- [GitHub workflow triggers](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow): token-trigger behavior and explicit dispatch.
- [AWS OIDC](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_oidc.html): temporary identity federation.
- Pinned action releases: [checkout v4.2.2](https://github.com/actions/checkout/releases/tag/v4.2.2), [upload-artifact v4.6.2](https://github.com/actions/upload-artifact/releases/tag/v4.6.2), [download-artifact v4.3.0](https://github.com/actions/download-artifact/releases/tag/v4.3.0).

Runtime library versions are intentionally not inferred from a tool brand. Test each adapter after installation. No native integration is claimed for a generic tool without a documented skills loader or an explicit instruction-file adapter.
