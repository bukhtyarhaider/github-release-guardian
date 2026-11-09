# Set up the testing copy

Staging is a separate copy of your app where people can try changes before customers see them.

Start with `audit`. Inspect existing provider files, workflows, environments, secret/variable names, README, and instruction files. Infer real build/test commands from the application's owning files. Identify runtime-only variables, migrations, production dependencies, and whether the output is static. Do not copy production databases or credentials.

The packaged deployment workflow supports AWS S3 static output. It is not a universal deployer for servers, containers, databases, or serverless functions. For Vercel, Netlify, Cloudflare, Hostinger, Kubernetes, or another existing provider, consult that provider's current official docs and implement an equivalent reviewed adapter. Until verified, keep `deployment.configured` false and report production blocked.

## AWS S3 adapter

1. With scoped authorization, create two dedicated buckets and HTTPS site URLs (typically CloudFront with an S3 origin), one each for testing and production. Enable bucket versioning and an appropriate retention policy for recovery. Keep S3 public access blocked when using a private origin. No bucket may contain unrelated content: deployment uses `s3 sync --delete` to remove stale site files.
2. Create the GitHub OIDC provider in AWS: issuer `https://token.actions.githubusercontent.com`, audience `sts.amazonaws.com`. Create two distinct IAM roles. Trust `repo:OWNER/REPO:environment:staging` for testing and `repo:OWNER/REPO:environment:production` for production; use exact `StringEquals` conditions for `sub` and `aud`. Review [AWS OIDC documentation](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_oidc.html).
3. Scope each role's policy to its own bucket only. See `assets/providers/aws-s3-policy.json` and `aws-oidc-trust.json` for substitution templates. No AWS keys are stored in chat or repository files. The runner exchanges an OIDC token for temporary credentials without printing them.
4. Configure GitHub environments named staging and production. Staging allows staging, release/*, and hotfix/* branches. Production allows only main, requires an independent reviewer, prevents self-review and administrator bypass. This restriction is essential because the AWS OIDC subject contains the environment rather than the branch.
5. Merge configured tests/build commands, output directory, region, bucket names, role ARNs, and HTTPS URLs into `.github/guardian/config.json`. The example `.yml` file is intentionally JSON (valid YAML 1.2); runtime configuration uses strict JSON and no YAML dependency. Set configured true only after reviewing isolation. No credentials belong in this file. Optional environment variable `GUARDIAN_SITE_URL` controls the URL displayed by GitHub; actual health verification uses configuration.
6. Verify the hosted runner has AWS CLI. If using another runner, install AWS CLI from the provider's verified distribution before running the deployment step. Tests and builds run in a separate job without cloud credentials.
7. Merge a small authorized setup change into staging. Inspect the entire Guardian candidate run and GitHub staging deployment. Open the testing copy; confirm feature behavior and `guardian-release.json` identifies the exact candidate commit. Record what was actually verified.

The candidate build writes a version marker, packs regular files only, and records SHA-256, candidate commit, repository, and run ID. Production downloads and verifies that same artifact. Builds expire after 30 days by default; revalidation is required after expiry. Configure longer retention within the repository's plan when necessary.

Health verification requests the home page and exact version marker over HTTPS. It cannot validate business behavior, a database migration, or every CDN edge. Keep the marker and HTML uncached or configure a short cache lifetime. Add provider-specific CDN invalidation and application probes if required before approving deployment. Never report this basic probe as full application acceptance.
