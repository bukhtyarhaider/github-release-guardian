"""Trusted GitHub Actions entrypoints. Builds have no deployment credentials."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import time
import urllib.parse
import urllib.request
import zipfile
from .core import Blocked, api, config, gh, git, pages, repository, run, sha
from .policy import validate_pr, version
from .release import candidate, head, verify_version
from .repository import ancestry, protection_errors, sync_state


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def command(argv):
    if not isinstance(argv, list) or not argv or not all(isinstance(x, str) and x for x in argv):
        raise Blocked("Configure a non-empty command argument list for testing and building.")
    # Build output stays in the unprivileged build job; long-running tests are supported.
    p = subprocess.run(argv, timeout=1800)
    if p.returncode:
        raise Blocked("An application test or build failed. Inspect the unprivileged build job.")


def build():
    cfg = config()
    if not cfg.get("deployment", {}).get("configured"):
        raise Blocked("Testing deployment is not configured. Local development can continue.")
    command(cfg.get("test_command"))
    command(cfg.get("build_command"))
    commit = sha(os.environ["GITHUB_SHA"])
    directory = Path(cfg["artifact_directory"]).resolve()
    project = Path.cwd().resolve()
    if directory == project or not directory.is_relative_to(project) or not directory.is_dir():
        raise Blocked("Build output must be a dedicated directory inside the project.")
    files = list(directory.rglob("*"))
    if not any(p.is_file() for p in files):
        raise Blocked("The build output is empty.")
    if any(p.is_symlink() or (p.is_file() and (p.name.startswith(".env") or p.name in {"credentials", "id_rsa"})) for p in files):
        raise Blocked("Build output contains a link or sensitive configuration file. Review its contents.")
    (directory / "guardian-release.json").write_text(json.dumps({"candidate_sha": commit}))
    out = Path(os.environ.get("RUNNER_TEMP", tempfile.gettempdir())) / "guardian-bundle"
    out.mkdir(parents=True, exist_ok=True)
    archive = out / "payload.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        for p in sorted(directory.rglob("*")):
            if p.is_file():
                tar.add(p, arcname=str(p.relative_to(directory)), recursive=False)
    manifest = {"schema": 1, "candidate_sha": commit, "sha256": digest(archive),
                "repository": os.environ["GITHUB_REPOSITORY"], "run_id": int(os.environ["GITHUB_RUN_ID"])}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    with open(os.environ["GITHUB_OUTPUT"], "a") as f:
        f.write(f"bundle={out}\n")


def unpack(bundle, target, expected_sha, repo, run_id):
    bundle, target = Path(bundle), Path(target)
    manifest = json.loads((bundle / "manifest.json").read_text())
    if (manifest.get("schema") != 1 or manifest.get("candidate_sha") != sha(expected_sha)
            or manifest.get("repository") != repo or manifest.get("run_id") != int(run_id)
            or manifest.get("sha256") != digest(bundle / "payload.tar.gz")):
        raise Blocked("The build identity or checksum does not match the tested candidate.")
    target.mkdir(parents=True, exist_ok=True)
    with tarfile.open(bundle / "payload.tar.gz", "r:gz") as tar:
        members = tar.getmembers()
        if len(members) > 100000 or sum(m.size for m in members) > 2 * 1024**3:
            raise Blocked("The build exceeds the supported static artifact size.")
        names = set()
        for m in members:
            path = target / m.name
            if not m.isfile() or not path.resolve().is_relative_to(target.resolve()) or m.name in names:
                raise Blocked("The build contains an unsafe archive entry.")
            names.add(m.name)
        for m in members:
            path = target / m.name
            path.parent.mkdir(parents=True, exist_ok=True)
            with tar.extractfile(m) as source, path.open("wb") as dest:
                shutil.copyfileobj(source, dest)
    marker = json.loads((target / "guardian-release.json").read_text())
    if marker != {"candidate_sha": expected_sha}:
        raise Blocked("The deployment marker does not match this release.")
    return manifest


def fetch_bundle(repo, evidence, target):
    # GitHub returns the immutable artifact selected from a trusted successful run.
    data = subprocess.run(["gh", "api", f"repos/{repo}/actions/artifacts/{int(evidence['artifact_id'])}/zip"],
                          capture_output=True, timeout=120)
    if data.returncode:
        raise Blocked("The tested build could not be downloaded. It may have expired.")
    from io import BytesIO
    target = Path(target)
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(BytesIO(data.stdout)) as z:
        if set(z.namelist()) != {"manifest.json", "payload.tar.gz"}:
            raise Blocked("The build artifact contains unexpected files.")
        if sum(x.file_size for x in z.infolist()) > 2 * 1024**3:
            raise Blocked("The build artifact exceeds the supported size.")
        for name in z.namelist():
            (target / name).write_bytes(z.read(name))


def deployment_config(cfg, environment):
    d = cfg["deployment"]
    if not d.get("configured") or d.get("provider") != "aws-s3":
        raise Blocked("A reviewed deployment adapter is required. This package includes AWS S3 static sites.")
    if environment not in {"staging", "production"}:
        raise Blocked("Unknown deployment environment.")
    a, b = d["staging"], d["production"]
    import re
    if not all(re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", x.get("bucket", "")) for x in (a, b)):
        raise Blocked("Configure valid, dedicated staging and production buckets.")
    if a["bucket"] == b["bucket"] or a.get("role_arn") == b.get("role_arn"):
        raise Blocked("Testing and production require different buckets and IAM roles.")
    for x in (a, b):
        u = urllib.parse.urlsplit(x.get("url", ""))
        if u.scheme != "https" or not u.hostname or u.username or u.password or u.query or u.fragment:
            raise Blocked("Configure an HTTPS site URL without credentials, a query, or a fragment.")
        if not re.fullmatch(r"arn:aws:iam::\d{12}:role/[A-Za-z0-9+=,.@_/-]+", x.get("role_arn", "")):
            raise Blocked("Configure an environment-specific AWS OIDC role.")
    if a["url"].rstrip("/") == b["url"].rstrip("/"):
        raise Blocked("Testing and production must use separate site URLs.")
    return d[environment], d["region"]


def aws_login(role, region):
    endpoint = os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"] + "&audience=sts.amazonaws.com"
    req = urllib.request.Request(endpoint, headers={"Authorization": "bearer " + os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"]})
    with urllib.request.urlopen(req, timeout=30) as r:
        token = json.load(r)["value"]
    response = run("aws", "sts", "assume-role-with-web-identity", "--role-arn", role,
                   "--role-session-name", "github-release-guardian", "--web-identity-token", token,
                   "--duration-seconds", "900", "--region", region, "--output", "json")
    credentials = json.loads(response)["Credentials"]
    # Never print STS credentials. Only the deployment subprocess inherits them.
    return {**os.environ, "AWS_ACCESS_KEY_ID": credentials["AccessKeyId"],
            "AWS_SECRET_ACCESS_KEY": credentials["SecretAccessKey"], "AWS_SESSION_TOKEN": credentials["SessionToken"],
            "AWS_DEFAULT_REGION": region}


def health(url, commit, attempts=12):
    for i in range(attempts):
        try:
            marker = url.rstrip("/") + "/guardian-release.json?guardian=" + commit
            req = urllib.request.Request(marker, headers={"Cache-Control": "no-cache"})
            with urllib.request.urlopen(req, timeout=15) as r:
                good = r.status == 200 and json.load(r) == {"candidate_sha": commit}
            with urllib.request.urlopen(url, timeout=15) as r:
                good = good and r.status == 200
            if good:
                return
        except (OSError, ValueError):
            pass
        if i + 1 < attempts:
            time.sleep(5)
    raise Blocked("The site has not confirmed this exact version. The release is incomplete; inspect hosting and CDN caches.")


def deploy(environment, bundle, expected_sha, repo, run_id):
    cfg = config()
    target, region = deployment_config(cfg, environment)
    with tempfile.TemporaryDirectory() as directory:
        manifest = unpack(bundle, directory, expected_sha, repo, run_id)
        env = aws_login(target["role_arn"], region)
        # Whole buckets are dedicated to this application; no shared prefixes.
        p = subprocess.run(["aws", "s3", "sync", directory, f"s3://{target['bucket']}/", "--delete", "--only-show-errors"],
                           env=env, capture_output=True, timeout=600)
        if p.returncode:
            raise Blocked("The hosting provider did not finish deploying. Inspect its permissions and service status.")
    health(target["url"], expected_sha)
    return manifest


def policy_check():
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    pr = event["pull_request"]
    repo = os.environ["GITHUB_REPOSITORY"]
    errors = validate_pr(pr["head"]["ref"], pr["base"]["ref"],
                         (pr["head"].get("repo") or {}).get("full_name") == repo, pr.get("body") or "")
    if pr["base"]["ref"] == "main" and not errors:
        cfg = config()
        errors.extend(protection_errors(repo, cfg))
        if not ancestry(repo, "main", pr["head"]["sha"])["main_ancestor"]:
            errors.append("This candidate does not include current production changes.")
        if not sync_state(repo)["complete"]:
            errors.append("Synchronize production into testing and active releases first.")
        candidate(repo, pr["head"]["sha"])
    if errors:
        raise Blocked(" ".join(errors))
    print("Ready: branch policy and available release evidence passed.")


def refresh_policy():
    """Post the required status from trusted base code, including after candidate completion."""
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    repo = os.environ["GITHUB_REPOSITORY"]
    if "pull_request" in event:
        numbers = [event["pull_request"]["number"]]
    elif "workflow_run" in event:
        commit = event["workflow_run"]["head_sha"]
        numbers = [p["number"] for p in pages(f"repos/{repo}/pulls?state=open") if p["head"]["sha"] == commit]
    else:
        numbers = [int(event["inputs"]["pr_number"])]
    for number in numbers:
        pr = api(f"repos/{repo}/pulls/{number}")
        errors = validate_pr(pr["head"]["ref"], pr["base"]["ref"], (pr["head"].get("repo") or {}).get("full_name") == repo, pr.get("body") or "")
        if pr["base"]["ref"] == "main" and not errors:
            try:
                cfg = config()
                errors.extend(protection_errors(repo, cfg))
                if not ancestry(repo, "main", pr["head"]["sha"])["main_ancestor"]:
                    errors.append("Synchronize current production into the candidate.")
                if not sync_state(repo)["complete"]:
                    errors.append("Synchronize production into testing and active releases.")
                candidate(repo, pr["head"]["sha"])
                verify_version(repo, cfg, pr)
            except Blocked as e:
                errors.append(str(e))
        api(f"repos/{repo}/statuses/{pr['head']['sha']}", "POST", {
            "state": "failure" if errors else "success", "context": "guardian-policy",
            "description": (errors[0] if errors else "Ready: branch and release policy passed")[:140]})
        for error in errors:
            print(error)


def production(number):
    repo, cfg = os.environ["GITHUB_REPOSITORY"], config()
    pr = api(f"repos/{repo}/pulls/{int(number)}")
    if not pr.get("merged") or pr["base"]["ref"] != "main" or (pr["head"].get("repo") or {}).get("full_name") != repo:
        raise Blocked("Production requires a merged release or urgent-fix request from this repository.")
    branch = pr["head"]["ref"]
    if not branch.startswith(("release/v", "hotfix/")):
        raise Blocked("This request cannot deploy production.")
    commit = sha(pr["head"]["sha"])
    merged = sha(pr["merge_commit_sha"])
    if head(repo, "main") != merged or os.environ["GITHUB_SHA"] != merged:
        raise Blocked("Production has moved since this release. Inspect the latest merged release before deploying.")
    merged_data = api(f"repos/{repo}/git/commits/{merged}")
    candidate_data = api(f"repos/{repo}/git/commits/{commit}")
    if (merged_data["tree"]["sha"] != candidate_data["tree"]["sha"] or len(merged_data["parents"]) != 2
            or merged_data["parents"][1]["sha"] != commit):
        raise Blocked("The production merge changed the tested content. Re-test a fresh candidate using merge commits.")
    verify_version(repo, cfg, pr, merged_data["parents"][0]["sha"])
    problems = protection_errors(repo, cfg)
    if problems:
        raise Blocked(" ".join(problems))
    build_evidence = candidate(repo, commit)
    if branch.startswith("release/"):
        tag = branch.removeprefix("release/")
        version(tag)
    else:
        # Determine the patch baseline BEFORE this merge, stable across retries.
        previous = merged_data["parents"][0]["sha"]
        tags = pages(f"repos/{repo}/tags")
        from .policy import version_key
        stable = []
        for t in tags:
            try:
                if version(t["name"])[3] is None and ancestry(repo, t["name"], previous)["main_ancestor"]:
                    stable.append(t["name"])
            except Blocked:
                continue
        if not stable:
            raise Blocked("Urgent fixes require an existing stable production version.")
        a, b, c, _ = version(max(stable, key=version_key))
        tag = f"v{a}.{b}.{c + 1}"
    releases = pages(f"repos/{repo}/releases")
    existing = next((r for r in releases if r["tag_name"] == tag), None)
    marker = f"<!-- guardian-pr:{number} candidate:{commit} -->"
    if existing and marker not in (existing.get("body") or ""):
        raise Blocked("This version belongs to another release. No files were replaced.")
    matching_tags = [t for t in pages(f"repos/{repo}/tags") if t["name"] == tag]
    if matching_tags and matching_tags[0]["commit"]["sha"] != merged:
        raise Blocked("This version tag points to different production content.")
    if existing and not existing["draft"]:
        print("Ready: this release is already published. No deployment was repeated.")
        return
    with tempfile.TemporaryDirectory() as directory:
        bundle = Path(directory) / "bundle"
        fetch_bundle(repo, build_evidence, bundle)
        # Verify before creating remote release records.
        unpack(bundle, Path(directory) / "verify", commit, repo, build_evidence["run_id"])
        if not matching_tags:
            api(f"repos/{repo}/git/refs", "POST", {"ref": f"refs/tags/{tag}", "sha": merged})
        if not existing:
            body = (f"## Version {tag.removeprefix('v')}\n\n### Changes\n{pr['title']} ([details]({pr['html_url']}))\n\n"
                    f"### Technical details\n- Tested candidate: `{commit}`\n- Production commit: `{merged}`\n"
                    f"- [Tests and staging verification]({build_evidence['run_url']})\n"
                    "- See the change request for user impact, migrations, and rollback instructions.\n\n" + marker)
            # Release PR already contains categorized, metadata-derived release notes.
            if branch.startswith("release/"):
                import re
                m = re.search(r"(?ms)^## Changes\n(.*?)(?=^## Important files)", pr.get("body") or "")
                if m:
                    user_notes = re.sub(r"(?m)^#(#{2,5}) ", r"\1 ", m[1].strip())
                    body = user_notes + f"\n\nProduction commit: `{merged}`\n\n" + marker
            existing = api(f"repos/{repo}/releases", "POST", {"tag_name": tag, "target_commitish": merged,
                           "name": f"Version {tag.removeprefix('v')}", "body": body, "draft": True,
                           "prerelease": version(tag)[3] is not None})
        manifest = deploy("production", bundle, commit, repo, build_evidence["run_id"])
        record = {**manifest, "version": tag, "production_sha": merged, "pr_number": int(number),
                  "production_run_id": int(os.environ["GITHUB_RUN_ID"]), "health": "verified"}
        record_path = Path(directory) / "deployment.json"
        record_path.write_text(json.dumps(record, indent=2))
        gh("release", "upload", tag, str(record_path), "--repo", repo, "--clobber")
        api(f"repos/{repo}/releases/{existing['id']}", "PATCH", {"draft": False})
    from .sync import synchronize
    result = synchronize(apply=True)
    print(f"Ready: {tag} was published and its production health was verified.")
    print(json.dumps(result))
