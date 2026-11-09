"""Pure policy decisions, usable offline and in trusted base-branch checks."""
import re
import unicodedata
from .core import Blocked

SEMVER = re.compile(r"^v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$")
TASK = re.compile(r"^(feat|bugfix|hotfix|docs|chore)/[a-z0-9]+(?:-[a-z0-9]+)*$")
IMPACTS = {"none": 0, "patch": 1, "minor": 2, "major": 3}


def version(value):
    match = SEMVER.fullmatch(value or "")
    if not match:
        raise Blocked("This project needs an explicit Semantic Versioning baseline, such as v1.0.0.")
    pre = match[4]
    if pre and any(x.isdigit() and len(x) > 1 and x.startswith("0") for x in pre.split(".")):
        raise Blocked("Prerelease numbers cannot contain leading zeroes.")
    return (*map(int, match.group(1, 2, 3)), pre)


def version_key(value):
    major, minor, patch, pre = version(value)
    identifiers = tuple((0, int(x)) if x.isdigit() else (1, x) for x in (pre or "").split("."))
    return major, minor, patch, pre is None, identifiers


def valid_branch(name):
    if name in ("main", "staging"):
        return True
    if name.startswith("release/v"):
        try:
            version(name.removeprefix("release/"))
            return True
        except Blocked:
            return False
    return bool(len(name) <= 100 and TASK.fullmatch(name))


def branch_name(request, kind="feat"):
    if kind not in {"feat", "bugfix", "hotfix", "docs", "chore"}:
        raise Blocked("Choose feature, bug fix, urgent fix, documentation, or maintenance.")
    text = unicodedata.normalize("NFKD", request).encode("ascii", "ignore").decode().lower()
    text = re.sub(r"^(?:please\s+)?(?:add|implement|create|fix|repair|update)\s+", "", text)
    slug = re.sub(r"[^a-z0-9]+", "-", text).strip("-")[:70].rstrip("-")
    if not slug:
        raise Blocked("Give this task a short description so I can name its workspace.")
    return f"{kind}/{slug}"


def validate_pr(head, base, same_repo=True, body=""):
    errors = []
    if not same_repo and base == "main":
        errors.append("Production candidates must belong to this repository.")
    if not valid_branch(head):
        errors.append("The work branch needs an approved name.")
    if base == "main":
        if not head.startswith(("release/", "hotfix/")):
            errors.append("Send ordinary work for testing before releasing it.")
    elif base == "staging":
        if head in ("main", "staging") or head.startswith("release/"):
            errors.append("Use a dedicated maintenance branch to synchronize production into testing.")
    elif not base.startswith("release/") or not head.startswith("chore/"):
        errors.append("Changes must go through testing; active releases accept synchronization PRs only.")
    for heading in ("Why", "Changes", "Important files", "Decisions", "Tests", "Status", "Remaining work", "Known problems", "Related", "Next steps"):
        match = re.search(rf"(?mi)^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)", body, re.S | re.M)
        if not match or not re.sub(r"<!--.*?-->", "", match[1], flags=re.S).strip():
            errors.append(f"Add the {heading.lower()} handoff section.")
    return errors


def impact(change):
    """Breaking always wins. Then highest explicit label, then Conventional Commit.

    Unknown metadata blocks. `release:none` conflicts with a recognized change.
    """
    message = change.get("message", "")
    labels = set(change.get("labels", []))
    breaking = bool(change.get("breaking") or "release:major" in labels or
                    re.search(r"(?m)^BREAKING[ -]CHANGE:\s*\S", message) or
                    re.match(r"^[a-z]+(?:\([^\n)]+\))?!:", message))
    if breaking:
        return "major"
    explicit = [k for k in IMPACTS if f"release:{k}" in labels]
    conventional = re.match(r"^([a-z]+)(?:\([^\n)]+\))?:\s+\S", message)
    inferred = None
    if conventional:
        t = conventional[1]
        inferred = "minor" if t == "feat" else "patch" if t in {"fix", "perf"} else "none" if t in {"docs", "chore", "test", "ci", "build", "style", "refactor", "revert"} else None
    if "none" in explicit and (inferred in {"patch", "minor"} or len(explicit) > 1):
        raise Blocked("The change has conflicting version labels. Should users get a fix, a feature, or a breaking update?")
    if explicit:
        return max(explicit, key=IMPACTS.get)
    if inferred is not None:
        return inferred
    raise Blocked("I need a version choice for an unclassified change: fix, feature, or breaking update?")


def calculate(current, changes, existing=(), initial="v0.1.0", prerelease=None):
    levels = [impact(c) for c in changes]
    level = max(levels, key=IMPACTS.get) if levels else "none"
    if level == "none":
        raise Blocked("There are no changes marked for a new release.")
    if current is None:
        a, b, c, pre = version(initial)
        if pre:
            raise Blocked("Use a stable initial baseline and a separate prerelease channel.")
    else:
        a, b, c, pre = version(current)
        # A prerelease already names the upcoming stable version.
        if pre is None:
            if level == "major":
                a, b, c = a + 1, 0, 0
            elif level == "minor":
                b, c = b + 1, 0
            else:
                c += 1
    result = f"v{a}.{b}.{c}"
    if prerelease:
        if not re.fullmatch(r"[a-z][a-z0-9-]*", prerelease):
            raise Blocked("Use a prerelease channel such as beta or rc.")
        n = 1
        while f"{result}-{prerelease}.{n}" in existing:
            n += 1
        result += f"-{prerelease}.{n}"
    if result in existing:
        raise Blocked("This version already exists. Resume its release or inspect the version history.")
    return {"version": result, "impact": level}


def release_errors(e):
    """Evidence schema is deliberately fail-closed. Live collection is in release.py."""
    errors = []
    for key, message in {
        "authenticated": "Connect GitHub first.",
        "can_push": "A repository writer must prepare the release.",
        "protections": "Repository protections need attention.",
        "staging_success": "The candidate has not completed its staging deployment.",
        "ci_success": "The required automatic checks have not passed.",
        "main_ancestor": "Production changes need synchronization into the candidate.",
        "sync_complete": "Production fixes are missing from testing or an active release.",
        "artifact_verified": "The tested artifact is missing or does not match.",
    }.items():
        if e.get(key) is not True:
            errors.append(message)
    if e.get("approvals", 0) < e.get("required_approvals", 1):
        errors.append("A required review is still pending.")
    if not e.get("candidate_sha") or e.get("candidate_sha") != e.get("tested_sha"):
        errors.append("The candidate changed after testing. Verify the updated candidate.")
    if e.get("duplicate"):
        errors.append("This version is already published.")
    if e.get("conflicts") is not False:
        errors.append("Two changes may affect the same part of the project. Resolve them first.")
    return errors
