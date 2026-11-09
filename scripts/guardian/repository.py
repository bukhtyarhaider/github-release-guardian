"""Read-only discovery and conflict-aware synchronization."""
import json
from pathlib import Path
import shutil
import subprocess
from urllib.parse import quote
from .core import Blocked, api, git, pages, report, repository, root


def ref(name):
    return quote(name, safe="")


def ancestry(repo, base, head):
    value = api(f"repos/{repo}/compare/{ref(base)}...{ref(head)}")
    return {"main_ancestor": value["status"] in {"ahead", "identical"},
            "status": value["status"], "ahead": value["ahead_by"], "behind": value["behind_by"]}


def sync_state(repo):
    branches = pages(f"repos/{repo}/branches")
    active = {p["head"]["ref"] for p in pages(f"repos/{repo}/pulls?state=open&base=main") if p["head"]["ref"].startswith("release/")}
    targets = [b["name"] for b in branches if b["name"] == "staging" or b["name"] in active]
    results = {b: ancestry(repo, "main", b) for b in targets}
    return {"complete": "staging" in results and all(v["main_ancestor"] for v in results.values()),
            "branches": results}


def conflict_state(base, head, cwd=None):
    """merge-tree computes a merge without touching index, working tree or refs."""
    p = subprocess.run(["git", "merge-tree", "--write-tree", base, head], cwd=cwd,
                       capture_output=True, text=True, timeout=120)
    if p.returncode not in (0, 1):
        raise Blocked("Conflict detection requires Git 2.38 or newer and complete branch history.")
    return p.returncode == 1


def protection_errors(repo, cfg):
    """Inspect effective branch rules, including inherited organization rules."""
    errors = []
    inspected_rulesets = set()
    for branch in ("main", "staging", "release/v0.0.0"):
        try:
            rules = pages(f"repos/{repo}/rules/branches/{branch}")
        except Blocked:
            errors.append(f"Cannot verify {branch} rules. An administrator must check the plan and permissions.")
            continue
        kinds = {r["type"] for r in rules}
        if not {"pull_request", "required_status_checks", "non_fast_forward", "deletion"} <= kinds:
            errors.append(f"{branch} needs pull requests, required checks, and protection from deletion and force pushes.")
        for r in rules:
            rule_id = r.get("ruleset_id")
            if rule_id and rule_id not in inspected_rulesets:
                inspected_rulesets.add(rule_id)
                try:
                    # Repository endpoint includes inherited rulesets by default.
                    details = api(f"repos/{repo}/rulesets/{rule_id}")
                    # GitHub hides this list from non-admin tokens. Effective PR/check
                    # enforcement still applies to those tokens; audit reports it unknown.
                    if details.get("bypass_actors"):
                        errors.append(f"A protection ruleset for {branch} permits bypass. Review it with an administrator.")
                except Blocked:
                    errors.append(f"Cannot verify bypass permissions for a {branch} protection ruleset.")
            p = r.get("parameters", {})
            if r["type"] == "pull_request":
                if p.get("required_approving_review_count", 0) < cfg.get("required_approvals", 1):
                    errors.append(f"{branch} needs the configured number of reviewers.")
                if not p.get("dismiss_stale_reviews_on_push") or not p.get("require_code_owner_review"):
                    errors.append(f"{branch} needs stale-review dismissal and code owner review.")
                if not p.get("require_last_push_approval") or p.get("allowed_merge_methods") != ["merge"]:
                    errors.append(f"{branch} needs independent latest-push review and merge commits only.")
            if r["type"] == "required_status_checks":
                checks = {x["context"] for x in p.get("required_status_checks", [])}
                if not set(cfg["required_checks"]) <= checks or not p.get("strict_required_status_checks_policy"):
                    errors.append(f"{branch} needs Guardian checks and up-to-date branches.")
                if any(x.get("integration_id") != 15368 for x in p.get("required_status_checks", []) if x["context"] in {"guardian-policy", "guardian-ci"}):
                    errors.append(f"{branch} Guardian checks must come from the GitHub Actions app.")
    try:
        tag_rulesets = [r for r in pages(f"repos/{repo}/rulesets") if r.get("target") == "tag" and r.get("enforcement") == "active"]
        protected = False
        for r in tag_rulesets:
            detail = api(f"repos/{repo}/rulesets/{r['id']}")
            refs = detail.get("conditions", {}).get("ref_name", {})
            kinds = {x["type"] for x in detail.get("rules", [])}
            if (not detail.get("bypass_actors") and not refs.get("exclude")
                    and any(x in {"refs/tags/v*", "refs/tags/**", "~ALL"} for x in refs.get("include", []))
                    and {"update", "deletion"} <= kinds):
                protected = True
        if not protected:
            errors.append("Version tags need active rules preventing changes and deletion without bypass.")
    except Blocked:
        errors.append("Version tag protection cannot be verified.")
    try:
        env = api(f"repos/{repo}/environments/production")
        if not any(x["type"] == "required_reviewers" and x.get("reviewers") and x.get("prevent_self_review") for x in env.get("protection_rules", [])):
            errors.append("Production needs a separate reviewer with self-review disabled.")
        if env.get("can_admins_bypass", True):
            errors.append("Production environment administrator bypass must be disabled.")
        if not (env.get("deployment_branch_policy") or {}).get("custom_branch_policies"):
            errors.append("Production deployments must be restricted to main.")
        policies = api(f"repos/{repo}/environments/production/deployment-branch-policies")["branch_policies"]
        if {(x["name"], x.get("type", "branch")) for x in policies} != {("main", "branch")}:
            errors.append("Production permits a branch or tag other than main.")
    except Blocked:
        errors.append("Production approval settings cannot be verified.")
    try:
        owner_errors = api(f"repos/{repo}/codeowners/errors?ref=main").get("errors", [])
        if owner_errors:
            errors.append("Production code owner configuration contains errors.")
        import base64
        owners = api(f"repos/{repo}/contents/.github/CODEOWNERS?ref=main")
        content = base64.b64decode(owners["content"]).decode()
        if not any(line.strip().startswith(("/.github/ ", "/.github/** ", ".github/** ", ".github/ ", "* ")) and "@" in line for line in content.splitlines() if not line.lstrip().startswith("#")):
            errors.append("Code owners must explicitly protect .github automation and its own ownership file.")
    except Blocked:
        errors.append("Production code owner configuration cannot be verified.")
    return errors


def audit():
    result = {"tools": {t: bool(shutil.which(t)) for t in ("git", "gh", "python3")}, "unknown": []}
    try:
        directory = root()
        result["local"] = {"branch": git("branch", "--show-current"),
                           "dirty": bool(git("status", "--porcelain")),
                           "branches": git("branch", "--format=%(refname:short)").splitlines()}
        groups = {
            "ci": [".github/workflows/*.yml", ".github/workflows/*.yaml"],
            "providers": ["vercel.json", "netlify.toml", "wrangler.toml", "fly.toml", "Dockerfile", "amplify.yml", "firebase.json", "render.yaml", "serverless.yml"],
            "instructions": ["AGENTS.md", "CLAUDE.md", ".agents/skills/*/SKILL.md", ".claude/skills/*/SKILL.md", ".agent/skills/*/SKILL.md"],
            "templates": ["README*", ".github/*template*", ".github/ISSUE_TEMPLATE/*"],
        }
        result["files"] = {k: sorted({str(p.relative_to(directory)) for pattern in patterns for p in directory.glob(pattern)}) for k, patterns in groups.items()}
        # Report variable NAMES only, never .env values or credential-bearing remotes.
        result["environment_files"] = [p.name for p in directory.glob(".env*")]
    except Blocked:
        return report("Needs attention", "This folder is not yet a Git project. Local skill use is available.", **result)
    try:
        repo = repository()
        result["repository"] = repo
        endpoints = {
            "metadata": f"repos/{repo}", "branches": f"repos/{repo}/branches",
            "rulesets": f"repos/{repo}/rulesets", "environments": f"repos/{repo}/environments",
            "secret_names": f"repos/{repo}/actions/secrets", "variables": f"repos/{repo}/actions/variables",
            "tags": f"repos/{repo}/tags", "releases": f"repos/{repo}/releases",
            "pull_requests": f"repos/{repo}/pulls?state=open", "runs": f"repos/{repo}/actions/runs?per_page=10",
            "main_rules": f"repos/{repo}/rules/branches/main", "staging_rules": f"repos/{repo}/rules/branches/staging",
        }
        for key, endpoint in endpoints.items():
            try:
                value = api(endpoint)
                if key == "metadata":
                    value = {k: value.get(k) for k in ("default_branch", "permissions", "private", "allow_merge_commit", "allow_squash_merge")}
                elif key == "secret_names":
                    value = [x["name"] for x in value["secrets"]]
                elif key == "variables":
                    value = [x["name"] for x in value["variables"]]
                elif key == "environments":
                    value = [{"name": x["name"], "protection_rules": x.get("protection_rules", []), "deployment_branch_policy": x.get("deployment_branch_policy")} for x in value["environments"]]
                    for environment in value:
                        for kind in ("secrets", "variables"):
                            try:
                                entries = api(f"repos/{repo}/environments/{ref(environment['name'])}/{kind}")[kind]
                                environment[f"{kind}_names"] = [x["name"] for x in entries]
                            except Blocked:
                                result["unknown"].append(f"{environment['name']} {kind}")
                elif key in {"branches", "tags", "releases", "pull_requests", "rulesets"}:
                    # Full enumeration for audit correctness.
                    value = pages(endpoint)
                    if key == "rulesets":
                        for ruleset in value:
                            try:
                                detail = api(f"repos/{repo}/rulesets/{ruleset['id']}")
                                if "bypass_actors" not in detail:
                                    result["unknown"].append(f"ruleset {ruleset['name']} bypass permissions (administrator audit required)")
                            except Blocked:
                                result["unknown"].append(f"ruleset {ruleset['name']} details")
                    fields = ("name", "tag_name", "draft", "number", "title", "html_url", "enforcement", "commit", "head", "base")
                    value = [{k: x[k] for k in fields if k in x} for x in value]
                elif key == "runs":
                    value = [{k: x.get(k) for k in ("name", "head_sha", "status", "conclusion", "html_url")} for x in value["workflow_runs"]]
                result[key] = value
            except Blocked:
                result["unknown"].append(key)
    except Blocked:
        result["unknown"].append("GitHub authentication or repository access")
    missing = []
    branches = {b["name"] for b in result.get("branches", [])}
    for b in ("main", "staging"):
        if b not in branches:
            missing.append(f"{b} branch")
    if not result.get("files", {}).get("ci"):
        missing.append("automatic checks")
    result["missing"] = missing
    return report("Needs attention" if missing or result["unknown"] else "Ready",
                  "Inspection complete. Review missing items and unknown settings before setup.", **result)
