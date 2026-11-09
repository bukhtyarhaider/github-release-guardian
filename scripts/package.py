#!/usr/bin/env python3
"""Create a distributable skill ZIP without caches, credentials or nested builds."""
import hashlib
from pathlib import Path
import zipfile
from guardian import __version__


def package():
    directory = Path(__file__).resolve().parents[1]
    out = directory / "dist"
    out.mkdir(exist_ok=True)
    target = out / f"github-release-guardian-{__version__}.zip"
    names = ["SKILL.md", "README.md", "LICENSE", "CONTRIBUTING.md", "SECURITY.md", "CODE_OF_CONDUCT.md", "AGENTS.md", "requirements-dev.txt", "agents", "scripts", "references", "assets", "docs", "adapters", "examples", "tests", ".github"]
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for name in names:
            path = directory / name
            files = [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file())
            for p in files:
                if "__pycache__" not in p.parts and p.suffix not in {".pyc", ".pyo"}:
                    z.write(p, Path("github-release-guardian") / p.relative_to(directory))
    checksum = hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix(".zip.sha256").write_text(f"{checksum}  {target.name}\n")
    print(target)
    return target


if __name__ == "__main__":
    package()
