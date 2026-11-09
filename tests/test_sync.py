from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from support import SHA
from guardian.repository import ancestry, conflict_state, sync_state


class Synchronization(unittest.TestCase):
    def test_divergence(self):
        with patch("guardian.repository.api", return_value=dict(status="diverged", ahead_by=2, behind_by=1)):
            self.assertFalse(ancestry("owner/repo", "main", "staging")["main_ancestor"])

    def test_staging_may_have_unreleased_work(self):
        with patch("guardian.repository.api", return_value=dict(status="ahead", ahead_by=8, behind_by=0)):
            self.assertTrue(ancestry("owner/repo", "main", "staging")["main_ancestor"])

    def test_only_active_release_branches_checked(self):
        branches = [{"name": x} for x in ("main", "staging", "release/v1.0.0", "release/v2.0.0")]
        prs = [{"head": {"ref": "release/v2.0.0"}}]
        with patch("guardian.repository.pages", side_effect=[branches, prs]), patch("guardian.repository.ancestry", return_value={"main_ancestor": True}):
            result = sync_state("owner/repo")
        self.assertEqual(set(result["branches"]), {"staging", "release/v2.0.0"})
        self.assertTrue(result["complete"])

    def test_missing_staging_blocks(self):
        with patch("guardian.repository.pages", side_effect=[[{"name": "main"}], []]):
            self.assertFalse(sync_state("owner/repo")["complete"])

    def test_real_merge_conflict_without_worktree_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            def git(*args):
                return subprocess.run(["git", *args], cwd=d, capture_output=True, text=True, check=True).stdout.strip()
            git("init", "-b", "main")
            git("config", "user.name", "Test")
            git("config", "user.email", "test@example.invalid")
            f = Path(d) / "file.txt"
            f.write_text("base\n")
            git("add", "file.txt")
            git("commit", "-m", "base")
            git("switch", "-c", "staging")
            f.write_text("staging\n")
            git("commit", "-am", "staging")
            git("switch", "main")
            f.write_text("production fix\n")
            git("commit", "-am", "fix")
            before = git("rev-parse", "HEAD")
            self.assertTrue(conflict_state("main", "staging", cwd=d))
            self.assertEqual(git("rev-parse", "HEAD"), before)
            self.assertEqual(f.read_text(), "production fix\n")
            self.assertEqual(git("status", "--porcelain"), "")

    def test_real_nonconflicting_merge(self):
        with tempfile.TemporaryDirectory() as d:
            def git(*args):
                return subprocess.run(["git", *args], cwd=d, capture_output=True, text=True, check=True).stdout
            git("init", "-b", "main")
            git("config", "user.name", "Test")
            git("config", "user.email", "test@example.invalid")
            (Path(d) / "file").write_text("base")
            git("add", "file")
            git("commit", "-m", "base")
            git("branch", "staging")
            self.assertFalse(conflict_state("main", "staging", cwd=d))
