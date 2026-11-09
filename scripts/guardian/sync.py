"""Create review requests for missing production ancestry; never auto-resolve conflicts."""
from .core import Blocked, api, pages, report, repository
from .release import handoff, head
from .repository import ancestry, ref, sync_state


def synchronize(apply=False):
    repo = repository()
    state = sync_state(repo)
    commit = head(repo, "main")
    planned = []
    for target, value in state["branches"].items():
        if value["main_ancestor"]:
            continue
        suffix = target.replace("/", "-").replace(".", "-")
        branch = f"chore/sync-{commit[:12]}-{suffix}"
        entry = {"target": target, "branch": branch}
        if apply:
            branches = pages(f"repos/{repo}/branches")
            existing = next((b for b in branches if b["name"] == branch), None)
            if existing and existing["commit"]["sha"] != commit:
                raise Blocked("An existing synchronization branch has changed. Review it before preparing another.")
            if not existing:
                api(f"repos/{repo}/git/refs", "POST", {"ref": f"refs/heads/{branch}", "sha": commit})
            prs = pages(f"repos/{repo}/pulls?state=open&base={ref(target)}")
            pr = next((p for p in prs if p["head"]["ref"] == branch), None)
            if not pr:
                body = handoff({"Why": "Keep the current production fixes in upcoming work.",
                    "Changes": f"Bring production commit {commit} into {target} through a reviewed merge.",
                    "Important files": "Inspect this pull request's file changes.",
                    "Decisions": "Preserve ancestry using a merge commit. Do not squash or force-push.",
                    "Tests": "Automatic checks will run on the proposed combined content.",
                    "Status": "Waiting for checks, conflict inspection, and required review.",
                    "Remaining work": "Resolve any conflicts on a dedicated branch and review the combined result.",
                    "Known problems": "GitHub may need a moment to calculate whether changes overlap.",
                    "Related": f"Production commit {commit}", "Next steps": "Review and merge; then run Guardian sync again to verify ancestry."})
                pr = api(f"repos/{repo}/pulls", "POST", {"head": branch, "base": target,
                         "title": f"chore: synchronize production into {target}", "body": body})
            entry["pr_url"] = pr["html_url"]
        planned.append(entry)
    return report("Needs attention" if planned else "Ready",
                  "Synchronization requests need review. Merge them with merge commits and verify again." if planned
                  else "Testing and active releases include current production changes.", requests=planned)
