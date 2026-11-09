# Something needs attention

Ask your agent: **“Explain what failed and safely continue.”** Give it the review request or deployment link if you have one. Keep passwords, tokens, and customer records out of chat.

If GitHub is disconnected, sign in using GitHub CLI's secure login flow. If a reviewer is needed, another authorized person must approve on GitHub. If testing failed, let the agent inspect the failure and fix it before trying to release.

If a release was interrupted, say **“Continue release request 42.”** The agent inspects its current state. A failed release can already have changed the public site, so it should explain what completed and what remains before retrying. Do not delete a release tag to start over.

If your testing copy has not been configured, local development is still available, but public releases are blocked. Your administrator or hosting helper can complete setup.

Technical recovery details are in the [recovery reference](../references/troubleshooting.md).
