# Example: a different agent resumes

User: “Continue release request 42. The previous agent stopped.”

The replacement agent reads the project README and PR handoff, then queries current GitHub state and candidate evidence. `resume --pr 42` does not depend on the previous machine's state file. It checks the candidate SHA, successful run, artifact retention, reviews, conflicts, current production ancestry, and synchronization.

If the PR already merged and production remains pending, the agent requests/resumes the protected production job within the user's authorization. If a matching draft release exists, the job resumes that version. If a published release already matches, it does not deploy again. If production advanced, it blocks an old deployment instead of rolling the site backward.

A failure after deployment but before publication is reported as partial progress: inspect site, tag, draft release, and job logs before retrying. “Needs attention. The public files changed, but the release record is incomplete” is appropriate only when verified by actual evidence.
