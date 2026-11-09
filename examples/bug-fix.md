# Example: a bug fix

User: “Fix broken checkout.”

The agent inspects the failure and begins bugfix/checkout-error from staging. It reproduces the issue, implements a focused change, runs the relevant checkout tests, and records actual outcomes. A title such as `fix: restore checkout after an expired session` describes the result.

“Save my progress” saves selected files locally. “Send my changes for testing” pushes the task branch and opens a staging PR with all handoff sections. The agent reports pending reviews separately from successful tests. It does not assume checkout is fixed on the public site until a later verified production release.
