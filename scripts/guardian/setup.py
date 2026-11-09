"""Reviewable installation and explicitly authorized repository settings."""
import json
from pathlib import Path
import shutil
from .core import Blocked, api, atomic_json, config, pages, report, repository, root


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE = SCRIPT_ROOT.parent if (SCRIPT_ROOT.parent / "assets").is_dir() else SCRIPT_ROOT


def files_plan(directory):
    directory = Path(directory)
    mapping = {}
    for source in SCRIPT_ROOT.rglob("*.py"):
        if "__pycache__" not in source.parts:
            mapping[directory / ".github/guardian" / source.relative_to(SCRIPT_ROOT)] = source
    for source in (PACKAGE / "assets").rglob("*"):
        if source.is_file():
            mapping[directory / ".github/guardian/assets" / source.relative_to(PACKAGE / "assets")] = source
    for folder, destination in (("workflows", ".github/workflows"), ("issue_templates", ".github/ISSUE_TEMPLATE")):
        for source in (PACKAGE / "assets" / folder).iterdir():
            mapping[directory / destination / source.name] = source
    mapping[directory / ".github/pull_request_template.md"] = PACKAGE / "assets/pull_request_template.md"
    mapping[directory / ".github/guardian/config.json"] = PACKAGE / "assets/config.example.yml"
    return mapping


def install_project(apply=False):
    directory = root()
    mapping = files_plan(directory)
    conflicts = [str(p.relative_to(directory)) for p, src in mapping.items() if p.exists() and p.read_bytes() != src.read_bytes()]
    if conflicts:
        raise Blocked("Existing files need a reviewed merge: " + ", ".join(conflicts) + ". No files were overwritten.")
    if apply:
        for p, source in mapping.items():
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, p)
    return report("Needs attention" if apply else "Ready",
                  "Setup files prepared. Configure real tests, build output, hosting, and code owners before submitting a setup PR."
                  if apply else "The setup plan is ready. Review the files before applying it.",
                  files=[str(p.relative_to(directory)) for p in mapping])


def apply_settings(reviewers, codeowners_verified=False):
    repo, cfg = repository(), config()
    metadata = api(f"repos/{repo}")
    if not metadata.get("permissions", {}).get("admin"):
        raise Blocked("A repository administrator must apply these protection settings.")
    if not codeowners_verified or not (root() / ".github/CODEOWNERS").is_file():
        raise Blocked("Set up real code owners first, then acknowledge that their access has been verified.")
    if not reviewers:
        raise Blocked("Choose at least one production reviewer who can review another person's deployment.")
    users = [{"type": "User", "id": api(f"users/{name}")["id"]} for name in reviewers]
    branches = pages(f"repos/{repo}/branches")
    main = next((b for b in branches if b["name"] == "main"), None)
    if main is None:
        raise Blocked("Import or rename the current production branch through a reviewed migration first.")
    if not any(b["name"] == "staging" for b in branches):
        api(f"repos/{repo}/git/refs", "POST", {"ref": "refs/heads/staging", "sha": main["commit"]["sha"]})
    # Namespaced rulesets coexist with existing rules; never delete others.
    existing = pages(f"repos/{repo}/rulesets")
    for filename in ("branches.json", "tags.json"):
        rules = json.loads((PACKAGE / "assets/rulesets" / filename).read_text())
        if filename == "branches.json":
            for rule in rules["rules"]:
                if rule["type"] == "pull_request":
                    rule["parameters"]["required_approving_review_count"] = cfg["required_approvals"]
        previous = next((r for r in existing if r["name"] == rules["name"]), None)
        api(f"repos/{repo}/rulesets" + (f"/{previous['id']}" if previous else ""), "PUT" if previous else "POST", rules)
    api(f"repos/{repo}", "PATCH", {"allow_merge_commit": True})
    # Existing staging restrictions and secrets are preserved.
    names = {x["name"] for x in api(f"repos/{repo}/environments")["environments"]}
    if "staging" not in names:
        api(f"repos/{repo}/environments/staging", "PUT", {"deployment_branch_policy": {"protected_branches": False, "custom_branch_policies": True}})
        for branch in ("staging", "release/*", "hotfix/*"):
            api(f"repos/{repo}/environments/staging/deployment-branch-policies", "POST", {"name": branch, "type": "branch"})
    # Do not replace an existing environment policy silently.
    if "production" in names:
        from .repository import protection_errors
        issues = protection_errors(repo, cfg)
        if issues:
            raise Blocked("Rulesets were applied. Existing production environment needs an administrator's reviewed update: " + " ".join(issues))
    else:
        api(f"repos/{repo}/environments/production", "PUT", {"reviewers": users, "prevent_self_review": True,
            "can_admins_bypass": False, "deployment_branch_policy": {"protected_branches": False, "custom_branch_policies": True}})
        api(f"repos/{repo}/environments/production/deployment-branch-policies", "POST", {"name": "main", "type": "branch"})
    return report("Needs attention", "Protection settings applied. Verify code owners, required checks and hosting before declaring setup complete.")
