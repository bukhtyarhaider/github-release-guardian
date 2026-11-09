"""GitHub-backed release preparation, evidence collection and resumable progress."""
import json
from pathlib import Path
from .core import Blocked, api, atomic_json, config, gh, git, lock, pages, report, repository
from .policy import calculate, release_errors, version, version_key
from .repository import ancestry, protection_errors, ref, sync_state


HANDOFF = ("Why", "Changes", "Important files", "Decisions", "Tests", "Status", "Remaining work", "Known problems", "Related", "Next steps")


def handoff(values):
    import re
    sections = []
    for heading in HANDOFF:
        value = values.get(heading, "None recorded; inspect the linked change before proceeding.")
        # Release notes can contain headings; keep them inside their handoff section.
        value = re.sub(r"(?m)^(#{1,5}) ", r"#\1 ", value)
        sections.append(f"## {heading}\n{value}")
    return "\n\n".join(sections) + "\n"


def head(repo, branch):
    return api(f"repos/{repo}/branches/{ref(branch)}")["commit"]["sha"]


def candidate(repo, commit):
    runs = api(f"repos/{repo}/actions/workflows/guardian-candidate.yml/runs?head_sha={commit}&per_page=100")["workflow_runs"]
    runs = [r for r in runs if r.get("event") in {"push", "workflow_dispatch"}]
    # A later failed/in-progress attempt invalidates an earlier successful attempt.
    if not runs:
        raise Blocked("The candidate has not run its testing deployment yet.")
    run = max(runs, key=lambda r: (r["run_number"], r.get("run_attempt", 1)))
    if run["conclusion"] != "success" or run["status"] != "completed":
        raise Blocked("The latest candidate checks or testing deployment are incomplete or failed.")
    if (run.get("head_repository") or {}).get("full_name") != repo:
        raise Blocked("Candidate evidence came from an unexpected repository or event.")
    artifacts = api(f"repos/{repo}/actions/runs/{run['id']}/artifacts?per_page=100")["artifacts"]
    matches = [a for a in artifacts if a["name"] == f"guardian-{commit}" and not a["expired"]]
    if len(matches) != 1:
        raise Blocked("The tested build is missing or expired. Re-run candidate validation.")
    deployments = pages(f"repos/{repo}/deployments?sha={commit}&environment=staging")
    success = False
    for d in deployments:
        statuses = pages(f"repos/{repo}/deployments/{d['id']}/statuses")
        if statuses and statuses[0]["state"] == "success":
            success = True
            break
    if not success:
        raise Blocked("No successful testing deployment exists for this exact candidate.")
    return {"run_id": run["id"], "artifact_id": matches[0]["id"], "sha": commit, "run_url": run["html_url"]}


def changes_since(repo, base, commit):
    # Compare is paginated: files are irrelevant, commits must all be classified.
    commits = []
    page = 1
    while True:
        data = api(f"repos/{repo}/compare/{ref(base)}...{commit}?per_page=100&page={page}")
        commits.extend(data["commits"])
        if len(data["commits"]) < 100:
            break
        page += 1
    changes, seen = [], set()
    for c in commits:
        prs = pages(f"repos/{repo}/commits/{c['sha']}/pulls")
        merged = [p for p in prs if p.get("merged_at") and p["base"]["ref"] == "staging"]
        if merged:
            for p in merged:
                if p["number"] not in seen:
                    seen.add(p["number"])
                    changes.append({"message": p["title"] + "\n" + (p.get("body") or ""),
                                    "labels": [x["name"] for x in p["labels"]], "url": p["html_url"], "sha": c["sha"]})
        else:
            # Ignore graph-only merge commits. Their children carry the metadata.
            if len(c.get("parents", [])) > 1:
                continue
            changes.append({"message": c["commit"]["message"], "sha": c["sha"]})
    return changes


def notes(number, changes, evidence):
    from .policy import impact
    sections = {"What's new": [], "What's fixed": [], "Improvements": [], "Important notes": []}
    for c in changes:
        level = impact(c)
        section = "Important notes" if level == "major" else "What's new" if level == "minor" else "What's fixed" if level == "patch" else "Improvements"
        title = c["message"].splitlines()[0]
        title = __import__("re").sub(r"^[a-z]+(?:\([^)]*\))?!?:\s*", "", title)
        sections[section].append(f"- {title}" + (f" ([change]({c['url']}))" if c.get("url") else ""))
    text = f"## Version {number.removeprefix('v')}\n"
    for title, entries in sections.items():
        if entries:
            text += f"\n### {title}\n" + "\n".join(entries) + "\n"
    text += ("\n### Technical details\n"
             f"- Tested commit: `{evidence['sha']}`\n- [Candidate checks and staging deployment]({evidence['run_url']})\n"
             f"- Build artifact ID: `{evidence['artifact_id']}`\n"
             "- Migration and rollback instructions: inspect the linked PR handoffs; unrecorded details require review.\n"
             "- Production status is recorded by the protected production workflow.\n")
    return text


def state_path():
    return Path(git("rev-parse", "--git-common-dir")).resolve() / "guardian-release.json"


def latest(repo, cfg):
    tags = pages(f"repos/{repo}/tags")
    stable = []
    for t in tags:
        try:
            if version(t["name"])[3] is None and ancestry(repo, t["name"], "main")["main_ancestor"]:
                stable.append(t["name"])
        except Blocked:
            continue
    if stable:
        return max(stable, key=version_key), [t["name"] for t in tags]
    if tags and not cfg.get("baseline_ref"):
        raise Blocked("Existing tags do not establish a stable version. Choose a baseline commit and initial version in setup.")
    return None, [t["name"] for t in tags]


def verify_version(repo, cfg, pr, production_base="main"):
    """A branch name is a request, never proof that its version is justified."""
    from .policy import impact
    branch = pr["head"]["ref"]
    if branch.startswith("hotfix/"):
        level = impact({"message": pr["title"] + "\n" + (pr.get("body") or ""),
                        "labels": [x["name"] for x in pr.get("labels", [])]})
        if level != "patch":
            raise Blocked("Urgent fixes must be compatible fixes. Use the normal release process for other version impacts.")
        return
    tag = branch.removeprefix("release/")
    _, _, _, pre = version(tag)
    import re
    if pre and not re.fullmatch(r"[a-z][a-z0-9-]*\.[1-9]\d*", pre):
        raise Blocked("Release prereleases need a channel and positive sequence, such as rc.1.")
    tags = pages(f"repos/{repo}/tags")
    # Exclude this reservation during an interrupted production attempt.
    existing = [t["name"] for t in tags if t["name"] != tag]
    stable = []
    for t in existing:
        try:
            if version(t)[3] is None and ancestry(repo, t, production_base)["main_ancestor"]:
                stable.append(t)
        except Blocked:
            continue
    current = max(stable, key=version_key) if stable else None
    if tags and not stable and not cfg.get("baseline_ref") and any(t["name"] != tag for t in tags):
        # Prerelease-only SemVer history can use the current production baseline.
        for t in existing:
            version(t)
    base = current or cfg.get("baseline_ref")
    if not base:
        base = head(repo, "main") if production_base == "main" else production_base
    changes = changes_since(repo, base, pr["head"]["sha"])
    expected = calculate(current, changes, existing, cfg["initial_version"], pre.rsplit(".", 1)[0] if pre else None)["version"]
    if tag != expected:
        raise Blocked(f"The candidate's version does not match its changes. The expected version is {expected}.")


def prepare(apply=False, prerelease=None):
    cfg, repo = config(), repository()
    permissions = api(f"repos/{repo}").get("permissions", {})
    if not permissions.get("push"):
        raise Blocked("You can inspect this project, but a repository writer must prepare its release.")
    problems = protection_errors(repo, cfg)
    if problems:
        raise Blocked(" ".join(problems))
    sync = sync_state(repo)
    if not sync["complete"]:
        raise Blocked("Production fixes must reach testing and all active release branches before release.")
    commit = head(repo, "staging")
    evidence = candidate(repo, commit)
    current, tags = latest(repo, cfg)
    if prerelease and current is None and not cfg.get("baseline_ref"):
        raise Blocked("Set the initial production baseline commit before the first prerelease so stable promotion can retain its change history.")
    base = current or cfg.get("baseline_ref") or head(repo, "main")
    changes = changes_since(repo, base, commit)
    calculated = calculate(current, changes, tags, cfg["initial_version"], prerelease)
    branch = f"release/{calculated['version']}"
    pending = [p for p in pages(f"repos/{repo}/pulls?state=open&base=main") if p["head"]["ref"].startswith(("release/", "hotfix/"))]
    other = [p for p in pending if p["head"]["ref"] != branch]
    if other:
        raise Blocked("Another production candidate is open. Finish or close it before preparing this release.")
    plan = {"repository": repo, "branch": branch, "version": calculated["version"], "candidate_sha": commit,
            "evidence": evidence, "notes": notes(calculated["version"], changes, evidence), "phase": "planned"}
    if not apply:
        return report("Ready", "The release plan is ready. Authorization will create its frozen branch and review request.", plan=plan)
    with lock():
        branches = pages(f"repos/{repo}/branches")
        existing = next((x for x in branches if x["name"] == branch), None)
        if existing and existing["commit"]["sha"] != commit:
            raise Blocked("That release branch already names a different candidate. Resume it or use a new version.")
        if not existing:
            # Ref creation is atomic on GitHub, serving as a cross-machine version reservation.
            api(f"repos/{repo}/git/refs", "POST", {"ref": f"refs/heads/{branch}", "sha": commit})
        plan["phase"] = "branch_created"
        atomic_json(state_path(), plan)
        body = handoff({"Why": f"Release {plan['version']} after testing.", "Changes": plan["notes"],
                        "Important files": "The frozen candidate contains the changes linked above.",
                        "Decisions": "Promote the exact tested artifact; merge commits preserve production ancestry.",
                        "Tests": f"Passed candidate run: {evidence['run_url']}. The release branch needs its own candidate run.",
                        "Status": "Waiting for release candidate checks and required reviews.", "Remaining work": "Approve, merge, and run the protected production workflow.",
                        "Known problems": "Inspect the linked PR handoffs for migration and rollback requirements.",
                        "Related": f"Candidate {commit}", "Next steps": "Ask Guardian to resume this release."})
        pr = next((p for p in pending if p["head"]["ref"] == branch), None)
        if pr is None:
            pr = api(f"repos/{repo}/pulls", "POST", {"title": f"chore: release {plan['version']}", "head": branch, "base": "main", "body": body})
        plan.update(pr_number=pr["number"], pr_url=pr["html_url"], phase="awaiting_validation")
        atomic_json(state_path(), plan)
        # Explicit dispatch does not depend on whether a ref API write emits a push event.
        api(f"repos/{repo}/actions/workflows/guardian-candidate.yml/dispatches", "POST", {"ref": branch})
    return report("Needs attention", "Release prepared. GitHub will test the frozen version; required reviews come next.", plan=plan)


def evidence_for_pr(repo, pr, cfg):
    commit = pr["head"]["sha"]
    verify_version(repo, cfg, pr)
    build = candidate(repo, commit)
    reviews = pages(f"repos/{repo}/pulls/{pr['number']}/reviews")
    latest_reviews = {}
    for review in reviews:
        if review["state"] in {"APPROVED", "CHANGES_REQUESTED", "DISMISSED"}:
            latest_reviews[review["user"]["login"]] = review
    approvals = sum(r["state"] == "APPROVED" and r.get("commit_id") == commit and r["user"]["login"] != pr["user"]["login"] for r in latest_reviews.values())
    evidence = {"authenticated": True, "can_push": bool(api(f"repos/{repo}").get("permissions", {}).get("push")),
                "protections": not protection_errors(repo, cfg), "candidate_sha": commit, "tested_sha": build["sha"],
                "ci_success": True, "staging_success": True, "artifact_verified": True,
                "main_ancestor": ancestry(repo, "main", commit)["main_ancestor"],
                "sync_complete": sync_state(repo)["complete"], "approvals": approvals,
                "required_approvals": cfg["required_approvals"], "conflicts": pr.get("mergeable") is not True,
                "duplicate": False}
    return evidence, build


def resume(number=None, merge=False, deploy=False):
    repo, cfg = repository(), config()
    if number is None:
        try:
            saved = json.loads(state_path().read_text())
            if saved["repository"] != repo:
                raise Blocked("Saved state belongs to another repository.")
            number = saved["pr_number"]
        except (OSError, ValueError, KeyError) as e:
            raise Blocked("Provide the release pull request number to recover from GitHub.") from e
    pr = api(f"repos/{repo}/pulls/{int(number)}")
    if pr["base"]["ref"] != "main" or not pr["head"]["ref"].startswith(("release/v", "hotfix/")):
        raise Blocked("This is not a production release request.")
    if not pr.get("merged"):
        evidence, build = evidence_for_pr(repo, pr, cfg)
        errors = release_errors(evidence)
        if errors:
            return report("Needs attention", " ".join(errors), pr_url=pr["html_url"])
        if not merge:
            return report("Ready", "The release passed validation. Its approved pull request can now be merged.", pr_url=pr["html_url"])
        # Expected SHA prevents merging a candidate changed after evidence collection.
        api(f"repos/{repo}/pulls/{number}/merge", "PUT", {"merge_method": "merge", "sha": pr["head"]["sha"]})
        pr = api(f"repos/{repo}/pulls/{number}")
        if not pr.get("merged"):
            raise Blocked("GitHub did not merge the release. Inspect required checks and reviews.")
    if deploy:
        api(f"repos/{repo}/actions/workflows/guardian-production.yml/dispatches", "POST",
            {"ref": "main", "inputs": {"pr_number": str(number)}})
        return report("Needs attention", "Production deployment requested. GitHub approval and health verification are still required.", pr_url=pr["html_url"])
    return report("Needs attention", "The release is merged. Resume with production deployment authorization to continue.", pr_url=pr["html_url"])
