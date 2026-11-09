from pathlib import Path
import subprocess
import tempfile
import unittest
from support import SHA

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/guardian.py"


class LocalCommands(unittest.TestCase):
    def git(self, directory, *args):
        return subprocess.run(["git", *args], cwd=directory, capture_output=True, text=True, check=True).stdout.strip()

    def test_start_and_save_with_real_remote(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            origin, seed, project = base / "remote.git", base / "seed", base / "project"
            subprocess.run(["git", "init", "--bare", str(origin)], capture_output=True, check=True)
            seed.mkdir()
            self.git(seed, "init", "-b", "main")
            self.git(seed, "config", "user.name", "Test")
            self.git(seed, "config", "user.email", "test@example.invalid")
            (seed / "readme").write_text("base")
            self.git(seed, "add", "readme")
            self.git(seed, "commit", "-m", "chore: initial")
            self.git(seed, "remote", "add", "origin", str(origin))
            self.git(seed, "push", "origin", "main")
            self.git(seed, "branch", "staging")
            self.git(seed, "push", "origin", "staging")
            subprocess.run(["git", "clone", "--branch", "staging", str(origin), str(project)], capture_output=True, check=True)
            self.git(project, "config", "user.name", "Test")
            self.git(project, "config", "user.email", "test@example.invalid")
            production_before = self.git(seed, "rev-parse", "main")
            p = subprocess.run(["python3", str(SCRIPT), "start", "Add Google login", "--apply"], cwd=project, capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual(self.git(project, "branch", "--show-current"), "feat/google-login")
            (project / "feature.txt").write_text("new feature")
            (project / ".env").write_text("TOKEN=not-a-real-secret")
            p = subprocess.run(["python3", str(SCRIPT), "save", "--file", "feature.txt", "--message", "feat: login", "--apply"], cwd=project, capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual(self.git(project, "show", "--format=", "--name-only", "HEAD"), "feature.txt")
            self.assertEqual(self.git(seed, "rev-parse", "main"), production_before)
            self.assertIn(".env", self.git(project, "status", "--porcelain"))
            p = subprocess.run(["python3", str(SCRIPT), "save", "--file", ".env", "--message", "oops", "--apply"], cwd=project, capture_output=True, text=True)
            self.assertEqual(p.returncode, 2)

    def test_save_refuses_main(self):
        with tempfile.TemporaryDirectory() as d:
            self.git(d, "init", "-b", "main")
            (Path(d) / "file").write_text("data")
            p = subprocess.run(["python3", str(SCRIPT), "save", "--file", "file", "--message", "fix: direct", "--apply"], cwd=d, capture_output=True, text=True)
            self.assertEqual(p.returncode, 2)
            self.assertIn("separate task", p.stderr)
