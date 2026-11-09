# Working with Guardian

Your agent is your interface. You do not have to invent workspace names or calculate version numbers.

Start with the outcome: “Let people sign in with Google.” The agent starts a separate workspace and keeps unfinished work away from your public version. “Save my progress” saves selected work locally. “Send it for testing” creates a review request; after review, the testing copy updates automatically when hosting is configured.

Try the feature in the testing copy. Tell the agent what worked and what did not. “Release the latest tested changes” prepares a numbered version, runs final checks, and requests the required approvals. A separate production approval lets the already tested build reach customers.

For a public-site emergency, say “Fix this production issue urgently.” The agent starts from the public version so unrelated unfinished features are not included. It keeps review and deployment safeguards.

Ask “What's completed and pending?” to see completed changes, outstanding checks, review requests, and incomplete releases. A completed merge is different from a verified public deployment. “Continue release request 42” helps another agent resume safely.

Ready means the current step succeeded or can proceed. Needs attention means a review, setup choice, or unfinished step remains. Blocked means proceeding would violate a requirement or essential access is missing. Each status should tell you what happens next.
