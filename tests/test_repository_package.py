import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from support import SHA, OTHER
from guardian.core import Blocked

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("repository_release", ROOT / ".github/repository_release.py")
REPO = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPO)


class RepositoryPackage(unittest.TestCase):
    def bundle(self, directory, bad_path=None):
        name = "github-release-guardian-1.0.0.zip"
        path = Path(directory) / name
        # A minimal real installable package, sufficient to execute the same smoke path.
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("github-release-guardian/SKILL.md", "skill")
            z.writestr("github-release-guardian/LICENSE", "MIT")
            z.writestr("github-release-guardian/scripts/install.py", "from pathlib import Path\nimport sys\nd=Path(sys.argv[-1])/'github-release-guardian/scripts'\nd.mkdir(parents=True)\n(d/'guardian.py').write_text(\"print('Ready')\")\n")
            z.writestr("github-release-guardian/scripts/guardian.py", "print('Ready')")
            if bad_path:
                z.writestr(bad_path, "unsafe")
        checksum = REPO.digest(path)
        (Path(directory) / (name + ".sha256")).write_text(f"{checksum}  {name}\n")
        m = {"schema": 1, "repository": "o/r", "candidate_sha": SHA, "run_id": 123,
             "version": "v1.0.0", "file": name, "sha256": checksum}
        (Path(directory) / "candidate.json").write_text(json.dumps(m))
        return m

    def test_verified_candidate_installs(self):
        with tempfile.TemporaryDirectory() as d:
            self.bundle(d)
            self.assertEqual(REPO.verify(d, "o/r", SHA, 123)["version"], "v1.0.0")

    def test_candidate_drift_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            self.bundle(d)
            with self.assertRaises(Blocked):
                REPO.verify(d, "o/r", OTHER, 123)

    def test_run_identity_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            self.bundle(d)
            with self.assertRaises(Blocked):
                REPO.verify(d, "o/r", SHA, 124)

    def test_tampered_zip_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            m = self.bundle(d)
            with (Path(d) / m["file"]).open("ab") as f:
                f.write(b"tamper")
            with self.assertRaises(Blocked):
                REPO.verify(d, "o/r", SHA, 123)

    def test_zip_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            self.bundle(d, "../escape")
            with self.assertRaises(Blocked):
                REPO.verify(d, "o/r", SHA, 123)

    def test_failed_latest_candidate_blocks(self):
        runs = {"workflow_runs": [{"head_repository": {"full_name": "o/r"}, "event": "push", "run_number": 2,
                                  "status": "completed", "conclusion": "failure"}]}
        with patch.object(REPO, "api", return_value=runs), self.assertRaises(Blocked):
            REPO.evidence("o/r", SHA)

    def test_expired_artifact_blocks(self):
        runs = {"workflow_runs": [{"head_repository": {"full_name": "o/r"}, "event": "push", "run_number": 2,
                                  "id": 123, "status": "completed", "conclusion": "success"}]}
        artifacts = {"artifacts": [{"name": f"package-{SHA}", "expired": True}]}
        with patch.object(REPO, "api", side_effect=[runs, artifacts]), self.assertRaisesRegex(Blocked, "expired"):
            REPO.evidence("o/r", SHA)

    def test_missing_production_reviewer_blocks(self):
        with patch.object(REPO, "api", return_value={"protection_rules": []}), self.assertRaisesRegex(Blocked, "reviewer"):
            REPO.require_production_gate("o/r")

    def test_administrator_bypass_blocks_publication(self):
        env = {"protection_rules": [{"type": "required_reviewers", "reviewers": [{"id": 1}], "prevent_self_review": True}],
               "can_admins_bypass": True, "deployment_branch_policy": {"custom_branch_policies": True}}
        with patch.object(REPO, "api", return_value=env), self.assertRaisesRegex(Blocked, "bypass"):
            REPO.require_production_gate("o/r")
