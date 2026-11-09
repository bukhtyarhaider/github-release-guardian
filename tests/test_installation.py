import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from support import SHA
from guardian.core import Blocked
from guardian.setup import files_plan, install_project

PACKAGE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("installer", PACKAGE / "scripts/install.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class Installation(unittest.TestCase):
    def test_install_invoke_and_uninstall(self):
        with tempfile.TemporaryDirectory() as d:
            installed = installer.install(d, aliases=True)
            self.assertTrue((installed / "SKILL.md").is_file())
            self.assertTrue((Path(d) / "github-release/SKILL.md").is_file())
            p = subprocess.run(["python3", str(installed / "scripts/guardian.py"), "help"], capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            (installed / "user-note.txt").write_text("retain this")
            installer.install(d, uninstall=True)
            self.assertFalse((installed / "SKILL.md").exists())
            self.assertEqual((installed / "user-note.txt").read_text(), "retain this")

    def test_modified_file_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            installed = installer.install(d)
            (installed / "SKILL.md").write_text("my changes")
            with self.assertRaises(ValueError):
                installer.install(d, update=True)
            self.assertEqual((installed / "SKILL.md").read_text(), "my changes")

    def test_unowned_alias_never_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            alias = Path(d) / "github-release/SKILL.md"
            alias.parent.mkdir()
            alias.write_text("other tool")
            with self.assertRaises(ValueError):
                installer.install(d, aliases=True)
            self.assertFalse((Path(d) / "github-release-guardian/SKILL.md").exists())
            self.assertEqual(alias.read_text(), "other tool")

    def test_update_removes_owned_alias_only(self):
        with tempfile.TemporaryDirectory() as d:
            installer.install(d, aliases=True)
            installer.install(d, update=True)
            self.assertFalse((Path(d) / "github-release/SKILL.md").exists())
            self.assertTrue((Path(d) / "github-release-guardian/SKILL.md").exists())

    def test_setup_preflight_preserves_existing_workflow(self):
        with tempfile.TemporaryDirectory() as d:
            workflow = Path(d) / ".github/workflows/guardian-ci.yml"
            workflow.parent.mkdir(parents=True)
            workflow.write_text("existing customized workflow")
            with patch("guardian.setup.root", return_value=Path(d)), self.assertRaises(Blocked):
                install_project(apply=True)
            self.assertEqual(workflow.read_text(), "existing customized workflow")
            self.assertFalse((Path(d) / ".github/guardian/config.json").exists())

    def test_setup_real_git_repository_and_installed_controller(self):
        with tempfile.TemporaryDirectory() as d:
            subprocess.run(["git", "init", "-b", "main", d], capture_output=True, check=True)
            with patch("guardian.setup.root", return_value=Path(d)):
                install_project(apply=True)
                install_project(apply=True)
            self.assertFalse(json.loads((Path(d) / ".github/guardian/config.json").read_text())["deployment"]["configured"])
            controller = Path(d) / ".github/guardian/guardian.py"
            p = subprocess.run(["python3", str(controller), "settings"], cwd=d, capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            p = subprocess.run(["python3", str(controller), "setup"], cwd=d, capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
