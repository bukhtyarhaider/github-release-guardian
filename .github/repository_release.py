#!/usr/bin/env python3
"""This repository's package publication adapter; downstream app logic stays canonical."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from guardian import __version__
from guardian.core import Blocked, api, gh, pages, sha
from guardian.policy import calculate, version, version_key, validate_pr
from guardian.release import changes_since, handoff, notes
from guardian.repository import ancestry


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify(bundle, repository, commit, run_id):
    bundle = Path(bundle)
    manifest = json.loads((bundle / "candidate.json").read_text())
    tag = manifest.get("version", "")
    version(tag)
    name = f"github-release-guardian-{tag.removeprefix('v')}.zip"
    if (manifest.get("schema") != 1 or manifest.get("repository") != repository
            or manifest.get("candidate_sha") != sha(commit) or manifest.get("run_id") != int(run_id)
            or manifest.get("file") != name or manifest.get("sha256") != digest(bundle / name)):
        raise Blocked("The candidate package identity or checksum does not match its verified build.")
    expected = f"{manifest['sha256']}  {name}"
    if (bundle / (name + ".sha256")).read_text().strip() != expected:
        raise Blocked("The published checksum does not match the candidate package.")
    # This is a trusted same-repository candidate, but reject archive tricks anyway.
    with zipfile.ZipFile(bundle / name) as z:
        names = z.namelist()
        if len(names) != len(set(names)) or len(names) > 10000 or sum(x.file_size for x in z.infolist()) > 100 * 1024**2:
            raise Blocked("The candidate ZIP has duplicate entries or exceeds the package size limit.")
        for item in z.infolist():
            path = Path(item.filename)
            if (path.is_absolute() or ".." in path.parts or not path.parts
                    or path.parts[0] != "github-release-guardian" or "\\" in item.filename
                    or (item.external_attr >> 16) & 0o170000 == 0o120000):
                raise Blocked("The candidate ZIP contains an unsafe path or link.")
        for path in ("SKILL.md", "LICENSE", "scripts/install.py", "scripts/guardian.py"):
            if f"github-release-guardian/{path}" not in names:
                raise Blocked("The candidate package is missing a required installation file.")
        with tempfile.TemporaryDirectory() as d:
            destination = Path(d)
            z.extractall(destination / "source")
            package = destination / "source/github-release-guardian"
            # Smoke-check with no GitHub or cloud credentials passed to package execution.
            env = {k: v for k, v in os.environ.items() if k in {"PATH", "LANG", "LC_ALL", "SYSTEMROOT"}}
            for command in ([sys.executable, str(package / "scripts/install.py"), "--agent", "generic", "--destination", str(destination / "skills")],
                            [sys.executable, str(destination / "skills/github-release-guardian/scripts/guardian.py"), "help"]):
                p = subprocess.run(command, env=env, capture_output=True, text=True, timeout=60)
                if p.returncode:
                    raise Blocked("The candidate package did not install or pass its help-command smoke check.")
    return manifest


def build():
    from guardian.core import git
    from importlib.util import module_from_spec, spec_from_file_location
    commit = sha(os.environ["GITHUB_SHA"])
    if git("rev-parse", "HEAD") != commit:
        raise Blocked("The checkout does not match the requested candidate.")
    spec = spec_from_file_location("guardian_package", ROOT / "scripts/package.py")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    archive = module.package()
    out = Path(os.environ["RUNNER_TEMP"]) / "guardian-candidate"
    out.mkdir(parents=True, exist_ok=True)
    for p in (archive, archive.with_suffix(".zip.sha256")):
        shutil.copy2(p, out / p.name)
    manifest = {"schema": 1, "repository": os.environ["GITHUB_REPOSITORY"], "candidate_sha": commit,
                "version": "v" + __version__, "run_id": int(os.environ["GITHUB_RUN_ID"]),
                "file": archive.name, "sha256": digest(archive)}
    (out / "candidate.json").write_text(json.dumps(manifest, indent=2) + "\n")
    verify(out, manifest["repository"], commit, manifest["run_id"])
    with open(os.environ["GITHUB_OUTPUT"], "a") as f:
        f.write(f"bundle={out}\n")


def evidence(repository, commit):
    runs = api(f"repos/{repository}/actions/workflows/repository-candidate.yml/runs?head_sha={sha(commit)}&per_page=100")["workflow_runs"]
    runs = [r for r in runs if r.get("event") in {"push", "workflow_dispatch"} and (r.get("head_repository") or {}).get("full_name") == repository]
    if not runs:
        raise Blocked("No same-repository candidate validation exists for this commit.")
    run = max(runs, key=lambda x: (x["run_number"], x.get("run_attempt", 1)))
    if run["status"] != "completed" or run["conclusion"] != "success":
        raise Blocked("The latest candidate package validation or staging verification has not passed.")
    artifacts = api(f"repos/{repository}/actions/runs/{run['id']}/artifacts?per_page=100")["artifacts"]
    found = [a for a in artifacts if a["name"] == f"package-{commit}" and not a["expired"]]
    if len(found) != 1:
        raise Blocked("The verified package artifact is missing or expired. Revalidate the candidate.")
    return {"run_id": run["id"], "artifact_id": found[0]["id"], "sha": commit, "run_url": run["html_url"]}


def require_production_gate(repository):
    env = api(f"repos/{repository}/environments/production")
    if not any(r.get("type") == "required_reviewers" and r.get("reviewers") and r.get("prevent_self_review") for r in env.get("protection_rules", [])):
        raise Blocked("Production needs an independent required reviewer and self-review prevention.")
    if env.get("can_admins_bypass", True) or not (env.get("deployment_branch_policy") or {}).get("custom_branch_policies"):
        raise Blocked("Production needs administrator bypass disabled and an explicit main-only deployment policy.")
    policies = api(f"repos/{repository}/environments/production/deployment-branch-policies")["branch_policies"]
    if {(p["name"], p.get("type", "branch")) for p in policies} != {("main", "branch")}:
        raise Blocked("Only the main branch may publish production packages.")
    rules = pages(f"repos/{repository}/rules/branches/main")
    if not {"pull_request", "required_status_checks", "deletion", "non_fast_forward"} <= {r["type"] for r in rules}:
        raise Blocked("Production branch protections are incomplete.")
    prs = [r.get("parameters", {}) for r in rules if r["type"] == "pull_request"]
    checks = {c["context"] for r in rules if r["type"] == "required_status_checks" for c in r.get("parameters", {}).get("required_status_checks", [])}
    if (not {"package-tests", "repository-policy"} <= checks
            or not any(p.get("required_approving_review_count", 0) >= 1 and p.get("require_code_owner_review") and p.get("dismiss_stale_reviews_on_push") for p in prs)):
        raise Blocked("Production requires package checks, source policy, and independent code owner review.")


def policy():
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    repository = os.environ["GITHUB_REPOSITORY"]
    if "pull_request" in event:
        numbers = [event["pull_request"]["number"]]
    elif "workflow_run" in event:
        numbers = [p["number"] for p in pages(f"repos/{repository}/pulls?state=open") if p["head"]["sha"] == event["workflow_run"]["head_sha"]]
    else:
        numbers = [int(event["inputs"]["pr_number"])]
    for number in numbers:
        pr = api(f"repos/{repository}/pulls/{number}")
        same = (pr["head"].get("repo") or {}).get("full_name") == repository
        branch, body = pr["head"]["ref"], pr.get("body") or ""
        # Authenticated Dependabot maintenance has a bounded adapter; user PRs cannot opt in.
        bot = same and pr["base"]["ref"] == "staging" and pr["user"]["login"] == "dependabot[bot]" and branch.startswith("dependabot/")
        if bot:
            branch = "chore/dependency-update"
            if not re.search(r"(?m)^## Why\s*$", body):
                body = handoff({"Why": "Update a tracked dependency.", "Changes": pr["title"] + "\n" + body,
                            "Important files": "See the dependency diff in this request.", "Decisions": "Keep independent owner review and all required package checks.",
                            "Tests": "See the current Package tests workflow; no result is assumed here.", "Status": "Needs attention: awaiting checks and review.",
                            "Remaining work": "Inspect compatibility, checks, and version impact before merging.", "Known problems": "Inspect the upstream dependency release notes.",
                               "Related": pr["html_url"], "Next steps": "An independent maintainer reviews this update."})
                api(f"repos/{repository}/pulls/{number}", "PATCH", {"body": body})
        errors = validate_pr(branch, pr["base"]["ref"], same, body)
        if pr["base"]["ref"] == "main" and not errors:
            try:
                if not ancestry(repository, "main", pr["head"]["sha"])["main_ancestor"]:
                    raise Blocked("Synchronize production into this candidate and revalidate it.")
                if not ancestry(repository, "main", "staging")["main_ancestor"]:
                    raise Blocked("Synchronize current production into staging before releasing.")
                evidence(repository, pr["head"]["sha"])
            except Blocked as e:
                errors.append(str(e))
        api(f"repos/{repository}/statuses/{pr['head']['sha']}", "POST", {
            "context": "repository-policy", "state": "failure" if errors else "success",
            "description": (errors[0] if errors else "Ready: branch routing, handoff, and required candidate evidence passed")[:140]})
        for error in errors:
            print(error)


def publish(number):
    repository = os.environ["GITHUB_REPOSITORY"]
    require_production_gate(repository)
    pr = api(f"repos/{repository}/pulls/{int(number)}")
    branch = pr["head"]["ref"]
    commit, merged = sha(pr["head"]["sha"]), sha(pr.get("merge_commit_sha"))
    if (not pr.get("merged") or pr["base"]["ref"] != "main" or not branch.startswith(("release/v", "hotfix/"))
            or (pr["head"].get("repo") or {}).get("full_name") != repository):
        raise Blocked("Publish only an approved, merged release or urgent-fix request from this repository.")
    if api(f"repos/{repository}/branches/main")["commit"]["sha"] != merged or os.environ["GITHUB_SHA"] != merged:
        raise Blocked("Production has moved. Do not publish an older request over a newer version.")
    merge_data = api(f"repos/{repository}/git/commits/{merged}")
    source = api(f"repos/{repository}/git/commits/{commit}")
    if (len(merge_data["parents"]) != 2 or merge_data["parents"][1]["sha"] != commit
            or source["tree"]["sha"] != merge_data["tree"]["sha"]):
        raise Blocked("The production merge differs from the exact tested candidate tree.")
    proof = evidence(repository, commit)
    with tempfile.TemporaryDirectory() as d:
        directory = Path(d)
        p = subprocess.run(["gh", "api", f"repos/{repository}/actions/artifacts/{proof['artifact_id']}/zip"], capture_output=True, timeout=120)
        if p.returncode:
            raise Blocked("Could not retrieve the verified candidate artifact.")
        import io
        with zipfile.ZipFile(io.BytesIO(p.stdout)) as z:
            if any(Path(n).name != n for n in z.namelist()) or sum(i.file_size for i in z.infolist()) > 100 * 1024**2:
                raise Blocked("The artifact container has unexpected paths or size.")
            z.extractall(directory)
        manifest = verify(directory, repository, commit, proof["run_id"])
        tag = manifest["version"]
        if branch.startswith("release/") and branch != "release/" + tag:
            raise Blocked("The release branch and built package version disagree.")
        previous = merge_data["parents"][0]["sha"]
        tags = pages(f"repos/{repository}/tags")
        prior = []
        for t in tags:
            try:
                if t["name"] != tag and version(t["name"])[3] is None and ancestry(repository, t["name"], previous)["main_ancestor"]:
                    prior.append(t["name"])
            except Blocked:
                continue
        current = max(prior, key=version_key) if prior else None
        changes = changes_since(repository, current or previous, commit)
        pre = version(tag)[3]
        if pre and not re.fullmatch(r"[a-z][a-z0-9-]*\.[1-9]\d*", pre):
            raise Blocked("A prerelease version needs a named channel and positive sequence.")
        expected = calculate(current, changes, [t["name"] for t in tags if t["name"] != tag],
                             initial="v1.0.0", prerelease=pre.rsplit(".", 1)[0] if pre else None)["version"]
        if expected != tag:
            raise Blocked(f"The version metadata requires {expected}, but this package is {tag}.")
        if current and version_key(tag) <= version_key(current):
            raise Blocked("The package version must advance beyond the current production version.")
        if branch.startswith("hotfix/"):
            if not current:
                raise Blocked("Urgent fixes require an existing stable production release.")
            a, b, c, _ = version(current)
            if tag != f"v{a}.{b}.{c + 1}":
                raise Blocked("An urgent fix must advance the current stable patch version.")
        marker = f"<!-- guardian-package-pr:{number} candidate:{commit} -->"
        existing = next((r for r in pages(f"repos/{repository}/releases") if r["tag_name"] == tag), None)
        if existing and marker not in (existing.get("body") or ""):
            raise Blocked("This version belongs to another release. No assets were changed.")
        tagged = next((t for t in tags if t["name"] == tag), None)
        if tagged and tagged["commit"]["sha"] != merged:
            raise Blocked("The version tag points to different content.")
        if existing and not existing["draft"]:
            print("Ready: this exact release is already published. No assets were replaced.")
            return
        if not tagged:
            api(f"repos/{repository}/git/refs", "POST", {"ref": f"refs/tags/{tag}", "sha": merged})
        if not existing:
            body = notes(tag, changes, proof) + f"\nProduction commit: `{merged}`\n\n" + marker
            existing = api(f"repos/{repository}/releases", "POST", {"tag_name": tag, "name": f"Version {tag.removeprefix('v')}",
                "target_commitish": merged, "draft": True, "prerelease": version(tag)[3] is not None, "body": body})
        record = {**manifest, "production_sha": merged, "pr_number": int(number), "production_run_id": int(os.environ["GITHUB_RUN_ID"]),
                  "verification": "exact candidate checksum and isolated installation smoke check passed"}
        (directory / "deployment.json").write_text(json.dumps(record, indent=2) + "\n")
        gh("release", "upload", tag, str(directory / manifest["file"]), str(directory / (manifest["file"] + ".sha256")),
           str(directory / "deployment.json"), "--repo", repository, "--clobber")
        api(f"repos/{repository}/releases/{existing['id']}", "PATCH", {"draft": False})
        print(f"Ready: {tag} published with the verified candidate ZIP, checksum, and deployment record.")
    # No broad repository token or self-approval is needed; the agent prepares sync PRs.
    print("Next: ask the authorized agent to synchronize production into staging and open release candidates through reviewed PRs.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["build", "verify", "policy", "publish"])
    parser.add_argument("--bundle")
    parser.add_argument("--pr", type=int)
    args = parser.parse_args()
    try:
        if args.action == "build":
            build()
        elif args.action == "verify":
            verify(args.bundle, os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_SHA"], os.environ["GITHUB_RUN_ID"])
            print("Ready: exact candidate package installed and smoke-checked successfully.")
        elif args.action == "policy":
            policy()
        elif args.pr:
            publish(args.pr)
        else:
            raise Blocked("Provide the merged release request number.")
    except (Blocked, OSError, ValueError, KeyError) as e:
        print("Blocked: " + (str(e) if isinstance(e, Blocked) else "inspect package configuration and remote state; success is not assumed"), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
