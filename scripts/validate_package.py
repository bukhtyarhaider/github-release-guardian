#!/usr/bin/env python3
"""Developer-only package checks. Requires PyYAML; runtime Guardian does not."""
import json
from pathlib import Path
import re
import sys
import yaml


def validate(directory):
    directory = Path(directory)
    errors = []
    for p in directory.rglob("*.md"):
        if any(x.startswith(".") for x in p.relative_to(directory).parts):
            continue
        for destination in re.findall(r"\[[^\]]*\]\(([^)]+)\)", p.read_text()):
            if re.match(r"\w+://|#", destination) or "$" in destination:
                continue
            target = destination.split("#")[0]
            if not (p.parent / target).exists():
                errors.append(f"Broken documentation link: {p.relative_to(directory)} -> {destination}")
    for p in directory.rglob("*.json"):
        json.loads(p.read_text())
    for p in directory.rglob("*.yml"):
        yaml.safe_load(p.read_text())
    yaml.safe_load((directory / "agents/openai.yaml").read_text())
    metadata = yaml.safe_load((directory / "SKILL.md").read_text().split("---", 2)[1])
    if metadata.get("name") != "github-release-guardian":
        errors.append("Skill name mismatch")
    workflows = {}
    for p in (directory / "assets/workflows").glob("*.yml"):
        data = yaml.load(p.read_text(), Loader=yaml.BaseLoader)
        workflows[p.stem] = data
        if "on" not in data or not data.get("jobs"):
            errors.append(f"Missing trigger/jobs in {p.name}")
        for job in data["jobs"].values():
            for step in job.get("steps", []):
                if "uses" in step and not re.fullmatch(r"[\w-]+/[\w-]+@[a-f0-9]{40}", step["uses"]):
                    errors.append(f"Unpinned external action in {p.name}")
    policy = workflows["guardian-policy"]
    for step in policy["jobs"]["evaluate"]["steps"]:
        if "uses" in step and "head" in step.get("with", {}).get("ref", ""):
            errors.append("Privileged workflow must not check out PR head")
    production = workflows["guardian-production"]["jobs"]["promote"]
    if production["environment"]["name"] != "production" or "refs/heads/main" not in production["if"]:
        errors.append("Production gate/ref is missing")
    if errors:
        raise ValueError("\n".join(errors))
    print("Package links, JSON/YAML, action pins, and workflow boundaries passed.")


if __name__ == "__main__":
    validate(Path(__file__).resolve().parents[1])
