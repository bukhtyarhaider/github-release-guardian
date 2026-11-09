#!/usr/bin/env python3
"""Copy one canonical skill and optional thin command aliases, with owned-file tracking."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

SOURCE = Path(__file__).resolve().parent.parent
NAME = "github-release-guardian"
COMMANDS = ("setup", "status", "start", "save", "submit", "test", "release", "hotfix", "sync", "help")
PATHS = {
    "codex": (".agents/skills", ".agents/skills"),
    "claude": (".claude/skills", ".claude/skills"),
    "antigravity": (".agents/skills", ".gemini/config/skills"),
}


def checksum(data):
    return hashlib.sha256(data).hexdigest()


def install(destination, aliases=False, update=False, uninstall=False):
    destination = Path(destination).resolve()
    folder = destination / NAME
    marker = folder / ".guardian-install.json"
    previous = json.loads(marker.read_text()) if marker.is_file() else {}
    if folder.exists() and not previous:
        raise ValueError("Destination is not an installer-owned skill. Choose another location.")
    if previous and not (update or uninstall):
        raise ValueError("Already installed. Use --update to refresh it.")
    if SOURCE == folder or folder.is_relative_to(SOURCE):
        raise ValueError("Install into the target project or user skills directory, outside this source package.")
    for relative, expected in previous.items():
        path = destination / relative
        if not path.resolve().is_relative_to(destination):
            raise ValueError("Invalid installation manifest path.")
        if path.exists() and (path.is_symlink() or checksum(path.read_bytes()) != expected):
            raise ValueError(f"Installed file was changed; preserve and review it first: {relative}")
    payload = {}
    if not uninstall:
        for name in ("SKILL.md", "README.md", "LICENSE", "CONTRIBUTING.md", "SECURITY.md", "CODE_OF_CONDUCT.md", "agents", "scripts", "references", "assets", "docs", "adapters", "examples"):
            source = SOURCE / name
            files = [source] if source.is_file() else [p for p in source.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
            for p in files:
                payload[str(Path(NAME) / p.relative_to(SOURCE))] = p.read_bytes()
        if aliases:
            for command in COMMANDS:
                name = f"github-{command}"
                text = (f"---\nname: {name}\ndescription: Run the {command} workflow through GitHub Release Guardian.\n---\n\n"
                        f"Read [the canonical skill](../{NAME}/SKILL.md), then follow its **{command}** intent. "
                        "Use the canonical scripts and references. Keep its authorization boundaries. "
                        "Pass along the user's arguments; do not interpret this alias as permission to publish.\n")
                payload[f"{name}/SKILL.md"] = text.encode()
        for relative in payload:
            path = destination / relative
            if not path.resolve().is_relative_to(destination) or path.is_symlink():
                raise ValueError("Destination contains an unexpected link.")
            if path.exists() and relative not in previous:
                raise ValueError(f"Would overwrite an unowned file: {relative}")
    # Preflight all conflicts before making any changes.
    for relative in previous.keys() - payload.keys():
        (destination / relative).unlink(missing_ok=True)
    for relative, data in payload.items():
        path = destination / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    if uninstall:
        marker.unlink(missing_ok=True)
        # Remove only empty owned directories; preserve additions made by the user.
        directories = {p for r in previous for p in (destination / r).parents if p != destination and p.is_relative_to(destination)}
        for p in sorted(directories, key=lambda x: len(x.parts), reverse=True):
            try:
                p.rmdir()
            except OSError:
                pass
    else:
        marker.write_text(json.dumps({r: checksum(data) for r, data in payload.items()}, indent=2) + "\n")
    return folder


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--agent", choices=[*PATHS, "generic"], required=True)
    p.add_argument("--scope", choices=["project", "user"], default="project")
    p.add_argument("--project", type=Path, default=Path.cwd())
    p.add_argument("--destination", type=Path, help="Required explicit skill-parent directory for generic tools")
    p.add_argument("--aliases", action="store_true", help="Install optional native command skills (Claude and Antigravity only)")
    p.add_argument("--update", action="store_true")
    p.add_argument("--uninstall", action="store_true")
    a = p.parse_args()
    try:
        if a.aliases and a.agent not in {"claude", "antigravity"}:
            raise ValueError("Codex uses $github-release-guardian plus natural language; generic tool commands depend on the host.")
        if a.agent == "generic" and not a.destination:
            raise ValueError("Choose --destination using your tool's official skills documentation.")
        destination = a.destination or ((a.project if a.scope == "project" else Path.home()) / PATHS[a.agent][a.scope == "user"])
        installed = install(destination, a.aliases, a.update, a.uninstall)
        print(("Removed owned skill files from " if a.uninstall else "Installed canonical skill at ") + str(installed))
        return 0
    except (OSError, ValueError) as e:
        print(f"Needs attention: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
