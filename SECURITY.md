# Security policy

## Reporting a vulnerability

Use [GitHub's private vulnerability reporting form](https://github.com/bukhtyarhaider/github-release-guardian/security/advisories/new). Do not publish exploit details, credentials, private repository contents, or customer data in an issue. If the private form is unavailable, open a public issue saying only that you need a private reporting channel, without disclosing the vulnerability.

Describe affected versions, the expected protection, the observed behavior, and minimal reproduction steps using disposable resources. Remove secrets and private data. Do not test against another person's repository or a production deployment without authorization.

## Supported versions

Security fixes target the latest stable release and the current main branch. Older releases may require an upgrade. Before a first stable release is published, report the affected commit. No response time or fix deadline is promised.

## Important boundaries

Guardian depends on GitHub's server-side protections, independent reviewers, trusted workflows, and properly scoped deployment roles. Skill instructions alone are not an access-control boundary. Administrators can change repository settings; use organizational policy where stronger central control is needed. Hash verification proves an artifact's identity, not that application code is safe.

Read [security and limitations](docs/security.md) before enabling automation on a real project. Never send tokens or passwords in chat. Missing checks or deployment evidence must block a release rather than be treated as success.
