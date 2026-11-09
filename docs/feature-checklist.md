# Delivery and activation checklist

| Feature | Included implementation | Activation needed |
| --- | --- | --- |
| Reusable skill | SKILL.md, routed references, OpenAI metadata | Install in the agent's documented location |
| Plain-language commands | Intent table, canonical CLI, optional alias skills | Verify discovery in the selected agent |
| Setup assistant | Read-only audit, plan/apply file generator | Select a real GitHub repository and authorize settings |
| Staging setup | Discovery guide, candidate build and deploy workflow | Configure real app commands and isolated hosting |
| Branch protections | Ruleset templates and settings command | Administrator review, real code owners, effective-rule check |
| PR enforcement | Trusted source policy and read-only application CI | Reviewed bootstrap onto the default branch |
| Automatic versioning | SemVer, labels, Conventional Commits, ambiguity blocking | Reliable metadata and a version baseline |
| Release workflow | Plan, frozen branch, PR, evidence checks, merge, dispatch | GitHub access and independent approvals |
| Changelog and GitHub Releases | Categorized notes, immutable version tag, draft/publish recovery | Actual authorized production run |
| Artifact promotion | Commit/run/repository identity and SHA-256 validation | Successful nonexpired candidate artifact |
| Production deployment | Protected S3 static-file promotion and health probes | Separate bucket/role/HTTPS URL and approval gate |
| Hotfixes | Production-based task path, patch release, protected PR | Stable production version and incident acceptance tests |
| Synchronization | Divergence inspection, deterministic chore branches/PRs | Review conflicts and merge with merge commits |
| Agent handoff | Required PR sections and continuation references | Truthful task-specific evidence and next steps |
| Platform adapters | Codex, Claude, Antigravity, documented generic adapter | Actual host discovery, execution and GitHub credentials |
| Installation lifecycle | Project/user install, owned-file updates/removal | Preserve any local edits before update |
| Automated tests | 81 unique tests and package CI | Run application-specific and live account rehearsals |
| Examples | Feature, bug, release, hotfix, recovery | Adapt outcomes to the actual project |
| Recovery | Local atomic state, remote PR recovery, draft-release retries | Inspect partial live state; authorize incident rollback if needed |
| Security/limitations | Least-privilege workflows, pinned actions, plan/provider boundaries | Administrator bypass audit, provider review, live verification |

No GitHub repository or hosting service was modified while building this package. See [validation evidence](validation.md) and [security boundaries](security.md).
