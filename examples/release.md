# Example: release tested work

User: “Release the latest tested changes.”

Agent: “Ready. The testing copy passed its checks. These changes add Google login, so the next version is 1.5.0.” This statement is appropriate only when the actual history and evidence support it.

The agent prepares release/v1.5.0 and a protected main PR, waits for the exact candidate to pass tests and staging deployment, then checks required reviews. “Needs attention. Another reviewer must approve this version on GitHub.” It provides the actual PR link.

After permitted merging, Guardian production awaits environment approval, promotes the same tested build, verifies the live marker, and publishes a release with deployment.json. The agent checks the actual run before saying the version is public, and reports any synchronization PRs still pending.
