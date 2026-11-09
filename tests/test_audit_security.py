import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from support import SHA
from guardian.core import Blocked, config, pages, run
from guardian.repository import audit, protection_errors
from guardian.setup import apply_settings


class AuditSecurity(unittest.TestCase):
    def test_command_failure_does_not_echo_credentials(self):
        from subprocess import CompletedProcess
        p = CompletedProcess(["gh"], 1, "token=secret-value", "https://secret-value@example.com")
        with patch("guardian.core.subprocess.run", return_value=p), self.assertRaises(Blocked) as e:
            run("gh", "api", "test")
        self.assertNotIn("secret-value", str(e.exception))

    def test_audit_missing_github_access_reports_unknown(self):
        with tempfile.TemporaryDirectory() as d:
            with patch("guardian.repository.root", return_value=Path(d)), patch("guardian.repository.git", return_value=""), patch("guardian.repository.repository", side_effect=Blocked("no login")):
                result = audit()
        self.assertIn("GitHub authentication or repository access", result["unknown"])
        self.assertEqual(result["status"], "Needs attention")

    def test_settings_require_admin(self):
        with patch("guardian.setup.repository", return_value="o/r"), patch("guardian.setup.config", return_value={}), patch("guardian.setup.api", return_value={"permissions": {"push": True, "admin": False}}) as api:
            with self.assertRaisesRegex(Blocked, "administrator"):
                apply_settings(["reviewer"], True)
        self.assertEqual(api.call_count, 1)

    def test_protections_fail_when_environment_is_unreadable(self):
        cfg = {"required_checks": ["guardian-policy", "guardian-ci"]}
        with patch("guardian.repository.pages", return_value=[]), patch("guardian.repository.api", side_effect=Blocked("permission denied")):
            problems = protection_errors("o/r", cfg)
        self.assertIn("Production approval settings cannot be verified.", problems)

    def test_pagination_does_not_miss_second_page(self):
        with patch("guardian.core.api", side_effect=[[{"number": i} for i in range(100)], [{"number": 100}]]) as api:
            values = pages("repos/o/r/pulls?state=open")
        self.assertEqual(len(values), 101)
        self.assertIn("&per_page=100&page=2", api.call_args.args[0])

    def test_unsafe_config_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "config.json"
            path.write_text(json.dumps({"schema": 1, "required_approvals": 0, "required_checks": [], "deployment": {}}))
            with self.assertRaises(Blocked):
                config(path)

    def test_default_config_accepted(self):
        package = Path(__file__).resolve().parents[1]
        self.assertFalse(config(package / "assets/config.example.yml")["deployment"]["configured"])
