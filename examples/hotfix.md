# Example: a public-site emergency

User: “The public checkout is broken. Fix it urgently.”

The agent starts hotfix/checkout-error from production, excluding unrelated staging work. It verifies the fix with focused tests and an exact-candidate staging deployment, then submits a protected main PR. Required reviews and deployment approval still apply.

If the previous production version was v1.5.0, the approved hotfix becomes v1.5.1. It promotes the same artifact, verifies public health, and creates synchronization requests so testing and active releases retain the fix. The agent verifies those requests after their reviewed merges; it does not report synchronization complete at creation time.
