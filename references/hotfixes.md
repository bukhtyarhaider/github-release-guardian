# Urgent production fixes

“Fix this urgent production problem” starts a hotfix branch from fetched origin/main, never from staging with unrelated features. Use `hotfix DESCRIPTION --apply`, save a tested fix, and submit a protected PR into main with the full handoff.

The hotfix push runs Guardian candidate, including exact-artifact staging deployment. Read-only PR CI, trusted source policy, current production ancestry, required reviews, and production environment approval still apply. Final acceptance must specifically check the incident's failure case. The `resume --pr N` controller works with hotfix PRs; ordinary release preparation is not needed.

After the merge, the production job derives a patch number from stable tags reachable before this hotfix merge. The same tested artifact is promoted and its health verified. It then prepares dedicated chore synchronization PRs into staging and open release branches. Review the combined changes and merge with merge commits. A release remains blocked while current production is absent from those targets.

Do not delete another candidate or cancel its approvals to force an urgent merge. Coordinate open production requests and refresh candidates that became stale after the fix. A hotfix that changes compatibility is not a routine patch: stop and use the normal major-release process. Urgency never grants permission to bypass protections.
