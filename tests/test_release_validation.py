import unittest
from unittest.mock import patch
from support import SHA, OTHER
from guardian.core import Blocked
from guardian.policy import release_errors
from guardian.release import candidate


class ReleaseValidation(unittest.TestCase):
    def setUp(self):
        self.evidence = dict(authenticated=True, can_push=True, protections=True, staging_success=True,
            ci_success=True, main_ancestor=True, sync_complete=True, artifact_verified=True,
            candidate_sha=SHA, tested_sha=SHA, approvals=1, required_approvals=1, conflicts=False, duplicate=False)

    def test_valid_evidence(self):
        self.assertEqual(release_errors(self.evidence), [])

    def test_missing_credentials(self):
        self.evidence["authenticated"] = False
        self.assertIn("Connect GitHub first.", release_errors(self.evidence))

    def test_missing_permission(self):
        self.evidence["can_push"] = False
        self.assertTrue(release_errors(self.evidence))

    def test_missing_staging(self):
        self.evidence["staging_success"] = False
        self.assertTrue(release_errors(self.evidence))

    def test_failed_ci(self):
        self.evidence["ci_success"] = False
        self.assertTrue(release_errors(self.evidence))

    def test_missing_approval(self):
        self.evidence["approvals"] = 0
        self.assertTrue(release_errors(self.evidence))

    def test_changed_candidate(self):
        self.evidence["tested_sha"] = OTHER
        self.assertTrue(release_errors(self.evidence))

    def test_missing_hotfix(self):
        self.evidence["sync_complete"] = False
        self.assertTrue(release_errors(self.evidence))

    def test_missing_fields_fail_closed(self):
        self.assertGreater(len(release_errors({})), 8)

    def test_unknown_conflicts_blocked(self):
        self.evidence["conflicts"] = None
        self.assertTrue(release_errors(self.evidence))

    def test_duplicate(self):
        self.evidence["duplicate"] = True
        self.assertTrue(release_errors(self.evidence))

    def test_latest_failed_run_invalidates_older_success(self):
        runs = {"workflow_runs": [dict(run_number=2, run_attempt=1, event="push", status="completed", conclusion="failure"),
                                 dict(run_number=1, run_attempt=1, event="push", status="completed", conclusion="success")]}
        with patch("guardian.release.api", return_value=runs), self.assertRaises(Blocked):
            candidate("owner/repo", SHA)

    def test_expired_artifact_blocks(self):
        responses = [{"workflow_runs": [dict(id=1, run_number=1, status="completed", conclusion="success", event="push", head_repository={"full_name": "owner/repo"})]},
                     {"artifacts": [dict(id=2, name=f"guardian-{SHA}", expired=True)]}]
        with patch("guardian.release.api", side_effect=responses), self.assertRaisesRegex(Blocked, "expired"):
            candidate("owner/repo", SHA)

    def test_successful_run_without_deployment_blocks(self):
        responses = [{"workflow_runs": [dict(id=1, run_number=1, status="completed", conclusion="success", event="push", head_repository={"full_name": "owner/repo"})]},
                     {"artifacts": [dict(id=2, name=f"guardian-{SHA}", expired=False)]}]
        with patch("guardian.release.api", side_effect=responses), patch("guardian.release.pages", return_value=[]), self.assertRaisesRegex(Blocked, "deployment"):
            candidate("owner/repo", SHA)
