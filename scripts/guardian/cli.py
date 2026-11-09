import argparse
import json
from subprocess import TimeoutExpired
import sys
from .core import Blocked, clean, config, gh, git, report, repository, root
from .policy import branch_name, calculate, valid_branch, validate_pr, release_errors


def parser():
    p = argparse.ArgumentParser(description="GitHub Release Guardian: plain-language release assistance")
    sub = p.add_subparsers(dest="action", required=True)
    for name in ("audit", "status", "test", "help"):
        sub.add_parser(name)
    setup = sub.add_parser("setup")
    setup.add_argument("--apply", action="store_true", help="Write the reviewed local setup files")
    settings = sub.add_parser("settings")
    settings.add_argument("--apply-settings", action="store_true", help="Explicit authorization to modify GitHub settings")
    settings.add_argument("--reviewer", action="append", default=[])
    settings.add_argument("--codeowners-verified", action="store_true")
    for name in ("start", "hotfix"):
        c = sub.add_parser(name)
        c.add_argument("description")
        c.add_argument("--kind", choices=["feat", "bugfix", "docs", "chore"], default="feat")
        c.add_argument("--worktree", help="Create an isolated Git worktree at this path")
        c.add_argument("--apply", action="store_true")
    save = sub.add_parser("save")
    save.add_argument("--file", action="append", default=[])
    save.add_argument("--message", required=True)
    save.add_argument("--apply", action="store_true")
    submit = sub.add_parser("submit")
    submit.add_argument("--title", required=True)
    submit.add_argument("--body-file", required=True)
    submit.add_argument("--apply", action="store_true")
    release = sub.add_parser("release")
    release.add_argument("--apply", action="store_true")
    release.add_argument("--prerelease")
    resume = sub.add_parser("resume")
    resume.add_argument("--pr", type=int)
    resume.add_argument("--merge", action="store_true", help="Authorize the approved GitHub merge")
    resume.add_argument("--deploy", action="store_true", help="Request protected production deployment")
    sync = sub.add_parser("sync")
    sync.add_argument("--apply", action="store_true")
    v = sub.add_parser("version")
    v.add_argument("--input", required=True, help="JSON: current, changes, existing, initial, prerelease")
    b = sub.add_parser("branch")
    b.add_argument("name")
    pr = sub.add_parser("validate-pr")
    pr.add_argument("--head", required=True)
    pr.add_argument("--base", required=True)
    pr.add_argument("--body-file", required=True)
    pr.add_argument("--fork", action="store_true")
    r = sub.add_parser("validate-release")
    r.add_argument("--input", required=True)
    pipe = sub.add_parser("pipeline")
    pipe.add_argument("operation", choices=["policy", "refresh-policy", "build", "deploy-staging", "production"])
    pipe.add_argument("--bundle")
    pipe.add_argument("--pr", type=int)
    return p


def execute(a):
    from pathlib import Path
    from .repository import audit
    if a.action in {"audit", "status"}:
        result = audit()
        if a.action == "status" and "repository" in result:
            from .repository import sync_state
            result["synchronization"] = sync_state(result["repository"])
        return result
    if a.action == "help":
        return report("Ready", "Tell me what you need: set up GitHub, start a feature, fix a bug, save work, send for testing, check testing, release, fix production, synchronize, or continue a release. Important external actions require authorization.")
    if a.action == "setup":
        from .setup import install_project
        return install_project(a.apply)
    if a.action == "settings":
        if not a.apply_settings:
            return report("Ready", "Plan: create missing staging from main, add Guardian rulesets, enable merge commits, and create protected environments. Existing production policies require manual review. No settings changed.")
        from .setup import apply_settings
        return apply_settings(a.reviewer, a.codeowners_verified)
    if a.action in {"start", "hotfix"}:
        name = branch_name(a.description, "hotfix" if a.action == "hotfix" else a.kind)
        base = "main" if a.action == "hotfix" else "staging"
        if a.apply:
            clean()
            git("fetch", "origin", base)
            if a.worktree:
                git("worktree", "add", "-b", name, str(Path(a.worktree).resolve()), f"origin/{base}")
            else:
                git("switch", "-c", name, f"origin/{base}")
        return report("Ready", "Your separate workspace is ready." if a.apply else "A separate workspace is planned.", branch=name, base=base)
    if a.action == "save":
        branch = git("branch", "--show-current")
        if branch in {"main", "staging"} or branch.startswith("release/") or not valid_branch(branch):
            raise Blocked("Start a separate task workspace before saving changes.")
        if not a.file:
            raise Blocked("Select the exact files to save after reviewing the changes for credentials.")
        for name in a.file:
            path = (root() / name).resolve()
            if not path.is_relative_to(root()) or any(x.startswith(".env") or x in {".git", ".aws", "id_rsa"} for x in path.relative_to(root()).parts):
                raise Blocked("A selected file is outside the project or may contain credentials.")
        if a.apply:
            if git("diff", "--cached", "--name-only"):
                raise Blocked("Other changes are already staged. Review them before saving selected files.")
            git("--literal-pathspecs", "add", "--", *a.file)
            git("commit", "-m", a.message)
        return report("Ready", "Selected work saved locally." if a.apply else "Selected work is ready for a local save. Review the diff first.", files=a.file)
    if a.action == "submit":
        branch = git("branch", "--show-current")
        if branch.startswith("release/"):
            raise Blocked("Use the release controller to submit a frozen release candidate.")
        base = "main" if branch.startswith("hotfix/") else "staging"
        body = Path(a.body_file).read_text()
        errors = validate_pr(branch, base, True, body)
        if errors:
            raise Blocked(" ".join(errors))
        if a.apply:
            from .core import api, pages
            clean()
            git("push", "--set-upstream", "origin", branch)
            repo = repository()
            prs = pages(f"repos/{repo}/pulls?state=open&base={base}")
            pr = next((p for p in prs if p["head"]["ref"] == branch and (p["head"].get("repo") or {}).get("full_name") == repo), None)
            if pr:
                api(f"repos/{repo}/pulls/{pr['number']}", "PATCH", {"title": a.title, "body": body})
            else:
                api(f"repos/{repo}/pulls", "POST", {"title": a.title, "head": branch, "base": base, "body": body})
        return report("Needs attention" if a.apply else "Ready", "The testing request is ready for automatic checks and review." if a.apply else "The request is ready to submit.", branch=branch, target=base)
    if a.action == "release":
        from .release import prepare
        return prepare(a.apply, a.prerelease)
    if a.action == "resume":
        from .release import resume
        return resume(a.pr, a.merge, a.deploy)
    if a.action == "sync":
        from .sync import synchronize
        return synchronize(a.apply)
    if a.action == "test":
        from .release import candidate, head
        repo = repository()
        e = candidate(repo, head(repo, "staging"))
        return report("Ready", "The current testing version passed checks and deployment health verification.", evidence=e)
    if a.action == "version":
        return calculate(**json.loads(Path(a.input).read_text()))
    if a.action == "branch":
        if not valid_branch(a.name):
            raise Blocked("Use an approved task, release, or urgent-fix workspace name.")
        return report("Ready", "Workspace name accepted.")
    if a.action == "validate-pr":
        errors = validate_pr(a.head, a.base, not a.fork, Path(a.body_file).read_text())
        if errors:
            raise Blocked(" ".join(errors))
        return report("Ready", "Supplied review-request policy passed; remote evidence is checked separately.")
    if a.action == "validate-release":
        errors = release_errors(json.loads(Path(a.input).read_text()))
        if errors:
            raise Blocked(" ".join(errors))
        return report("Ready", "Supplied evidence passed the offline policy validator; live GitHub verification is still required.")
    if a.action == "pipeline":
        import os
        from . import pipeline
        if a.operation == "policy":
            pipeline.policy_check()
        elif a.operation == "refresh-policy":
            pipeline.refresh_policy()
        elif a.operation == "build":
            pipeline.build()
        elif a.operation == "deploy-staging":
            pipeline.deploy("staging", a.bundle, os.environ["GITHUB_SHA"], os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_RUN_ID"])
        else:
            if not a.pr:
                raise Blocked("A release request number is required.")
            pipeline.production(a.pr)
        return report("Ready", "This pipeline step completed successfully.")


def main():
    try:
        value = execute(parser().parse_args())
        print(json.dumps(value, indent=2))
        return 0
    except (Blocked, OSError, ValueError, KeyError, TimeoutExpired) as e:
        print(json.dumps(report("Blocked", str(e) if isinstance(e, Blocked) else "The operation could not finish. Inspect configuration and service availability; no success is assumed.")), file=sys.stderr)
        return 2
