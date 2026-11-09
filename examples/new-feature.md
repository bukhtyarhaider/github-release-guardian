# Example: a new feature

User: “Add Google login.”

Agent: “Ready. I'll start a separate workspace for the login change.” It derives feat/google-login from current staging, checks for unsaved work, and creates the branch under the user's task authorization.

After implementation it runs the app's relevant tests, records the handoff, saves selected files, and creates a review into staging when asked to send for testing. It waits for actual GitHub checks and reviews. After merging, it verifies the staging deployment before saying the testing copy is ready.

A useful PR title is `feat: add Google login`. If an existing sign-in API changes incompatibly, record the breaking declaration; do not hide it behind the feature label.
