import unittest
from support import handoff
from guardian.policy import branch_name, valid_branch, validate_pr


class BranchPolicy(unittest.TestCase):
    def test_task_names(self):
        for name in ["feat/google-login", "bugfix/checkout-error", "hotfix/payment", "docs/readme", "chore/deps", "main", "staging", "release/v1.2.0", "release/v1.2.0-rc.1"]:
            with self.subTest(name=name):
                self.assertTrue(valid_branch(name))

    def test_invalid_names(self):
        for name in ["dev", "feat/UPPER", "feat/a b", "feat/../main", "feat/-x", "feat/x-", "release/v01.0.0", "release/v1.0.0-rc.01", "release/1.0.0", "feature/foo", "chore/x;touch-secret"]:
            with self.subTest(name=name):
                self.assertFalse(valid_branch(name))

    def test_natural_names(self):
        self.assertEqual(branch_name("Add Google login."), "feat/google-login")
        self.assertEqual(branch_name("Fix broken checkout", "bugfix"), "bugfix/broken-checkout")

    def test_feature_main_forbidden(self):
        self.assertTrue(validate_pr("feat/login", "main", body=handoff()))

    def test_release_main_allowed(self):
        self.assertEqual(validate_pr("release/v1.2.0", "main", body=handoff()), [])

    def test_hotfix_main_allowed(self):
        self.assertEqual(validate_pr("hotfix/checkout", "main", body=handoff()), [])

    def test_fork_production_forbidden(self):
        self.assertTrue(validate_pr("release/v1.2.0", "main", False, handoff()))

    def test_main_staging_forbidden_but_sync_allowed(self):
        self.assertTrue(validate_pr("main", "staging", body=handoff()))
        self.assertEqual(validate_pr("chore/sync-main", "staging", body=handoff()), [])

    def test_active_release_sync(self):
        self.assertEqual(validate_pr("chore/sync-main", "release/v1.2.0", body=handoff()), [])
        self.assertTrue(validate_pr("feat/login", "release/v1.2.0", body=handoff()))

    def test_blank_handoff_comments_rejected(self):
        from pathlib import Path
        body = (Path(__file__).resolve().parents[1] / "assets/pull_request_template.md").read_text()
        self.assertTrue(validate_pr("feat/login", "staging", body=body))
