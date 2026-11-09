"""Small, explicit process and GitHub boundaries. Never invoke a shell."""
import contextlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


class Blocked(RuntimeError):
    pass


def run(*args, cwd=None, ok=(0,), input=None):
    try:
        p = subprocess.run(list(map(str, args)), cwd=cwd, input=input,
                           text=True, capture_output=True, timeout=120)
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        raise Blocked(f"Could not run {args[0]}. Check installation and connectivity.") from e
    if p.returncode not in ok:
        # Raw subprocess output may contain remote URLs with embedded credentials.
        raise Blocked(f"{args[0]} could not complete {args[1] if len(args) > 1 else 'the operation'}. "
                      "Inspect the tool locally; credentials and raw logs are omitted.")
    return p.stdout.strip()


def git(*args, cwd=None):
    return run("git", *args, cwd=cwd)


def gh(*args):
    return run("gh", *args)


def api(endpoint, method="GET", data=None):
    args = ["api", endpoint, "--method", method,
            "-H", "Accept: application/vnd.github+json"]
    if data is not None:
        args += ["--input", "-"]
    output = run("gh", *args, input=json.dumps(data) if data is not None else None)
    return json.loads(output) if output else None


def pages(endpoint):
    """Paginate list endpoints; never silently inspect only the first page."""
    out = []
    page = 1
    while True:
        batch = api(f"{endpoint}{'&' if '?' in endpoint else '?'}per_page=100&page={page}")
        if not isinstance(batch, list):
            raise Blocked("Expected a paginated GitHub list.")
        out.extend(batch)
        if len(batch) < 100:
            return out
        page += 1


def root():
    return Path(git("rev-parse", "--show-toplevel"))


def repository():
    value = json.loads(gh("repo", "view", "--json", "nameWithOwner"))["nameWithOwner"]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value):
        raise Blocked("GitHub returned an invalid repository name.")
    return value


def config(path=None):
    path = Path(path) if path else root() / ".github/guardian/config.json"
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError) as e:
        raise Blocked("Project setup is incomplete. Ask me to set up GitHub Release Guardian.") from e
    if not isinstance(data, dict) or data.get("schema") != 1:
        raise Blocked("Unsupported Guardian configuration version.")
    if (type(data.get("required_approvals")) is not int or not 1 <= data["required_approvals"] <= 6
            or not isinstance(data.get("required_checks"), list)
            or not all(isinstance(x, str) for x in data["required_checks"])
            or not {"guardian-policy", "guardian-ci"} <= set(data["required_checks"])
            or not isinstance(data.get("deployment"), dict)):
        raise Blocked("Configuration must retain required Guardian checks, independent reviews, and deployment settings.")
    return data


def clean():
    if git("status", "--porcelain"):
        raise Blocked("Your work has unsaved changes. Save them before switching or releasing.")


def sha(value):
    if not re.fullmatch(r"[0-9a-f]{40}", value or ""):
        raise Blocked("Expected an exact commit identifier.")
    return value


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".guardian-")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


@contextlib.contextmanager
def lock():
    """OS lock releases after interruption; shared by worktrees."""
    import fcntl
    directory = Path(git("rev-parse", "--git-common-dir")).resolve()
    with (directory / "guardian.lock").open("a") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as e:
            raise Blocked("Another Guardian operation is running. Wait for it to finish.") from e
        yield


def report(status, message, **details):
    return {"status": status, "message": message, **details}
