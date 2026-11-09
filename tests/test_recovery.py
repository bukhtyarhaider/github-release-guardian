from contextlib import nullcontext
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from support import SHA, OTHER
from guardian.core import Blocked
from guardian import pipeline, release
import test_artifacts

MERGE = "c" * 40


class Recovery(unittest.TestCase):
    def test_resume_on_another_machine_uses_pr_number(self):
        pr = dict(number=42, base={"ref": "main"}, head={"ref": "release/v1.1.0", "sha": SHA}, merged=True, html_url="https://github.com/o/r/pull/42")
        calls = []
        def remote(endpoint, method="GET", data=None):
            calls.append((endpoint, method, data))
            return pr if endpoint.endswith("/pulls/42") else None
        with patch("guardian.release.repository", return_value="o/r"), patch("guardian.release.config", return_value={}), patch("guardian.release.api", side_effect=remote), patch("guardian.release.state_path", side_effect=AssertionError("local state must not be read")):
            result = release.resume(42, deploy=True)
        self.assertEqual(result["status"], "Needs attention")
        self.assertEqual(calls[-1][2], {"ref": "main", "inputs": {"pr_number": "42"}})

    def test_failed_merge_response_never_reported_as_merged(self):
        pr = dict(number=42, base={"ref": "main"}, head={"ref": "release/v1.1.0", "sha": SHA}, merged=False, html_url="https://github.com/o/r/pull/42")
        with patch("guardian.release.repository", return_value="o/r"), patch("guardian.release.config", return_value={}), patch("guardian.release.api", return_value=pr), patch("guardian.release.evidence_for_pr", return_value=({}, {})), patch("guardian.release.release_errors", return_value=[]):
            with self.assertRaisesRegex(Blocked, "did not merge"):
                release.resume(42, merge=True)

    def test_branch_reservation_survives_interrupted_pr_creation(self):
        state = {"branch": False, "fail": True}
        cfg = {"initial_version": "v0.1.0"}
        def remote(endpoint, method="GET", data=None):
            if endpoint == "repos/o/r":
                return {"permissions": {"push": True}}
            if endpoint.endswith("/git/refs"):
                self.assertFalse(state["branch"])
                state["branch"] = True
                return {}
            if endpoint.endswith("/pulls"):
                from guardian.policy import validate_pr
                self.assertEqual(validate_pr(data["head"], data["base"], body=data["body"]), [])
                if state["fail"]:
                    raise Blocked("Simulated interruption")
                return {"number": 42, "html_url": "https://github.com/o/r/pull/42"}
            if endpoint.endswith("/dispatches"):
                return None
            raise AssertionError(endpoint)
        def lists(endpoint):
            if endpoint.endswith("/branches"):
                return [{"name": "release/v1.1.0", "commit": {"sha": SHA}}] if state["branch"] else []
            return []
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "state.json"
            with patch("guardian.release.repository", return_value="o/r"), patch("guardian.release.config", return_value=cfg), patch("guardian.release.api", side_effect=remote), patch("guardian.release.pages", side_effect=lists), patch("guardian.release.protection_errors", return_value=[]), patch("guardian.release.sync_state", return_value={"complete": True}), patch("guardian.release.head", return_value=SHA), patch("guardian.release.candidate", return_value={"sha": SHA, "artifact_id": 9, "run_url": "https://github.com/o/r/actions/runs/9"}), patch("guardian.release.latest", return_value=("v1.0.0", ["v1.0.0"])), patch("guardian.release.changes_since", return_value=[{"message": "feat: login"}]), patch("guardian.release.state_path", return_value=path), patch("guardian.release.lock", return_value=nullcontext()):
                with self.assertRaisesRegex(Blocked, "interruption"):
                    release.prepare(apply=True)
                self.assertEqual(json.loads(path.read_text())["phase"], "branch_created")
                state["fail"] = False
                result = release.prepare(apply=True)
                self.assertEqual(result["plan"]["pr_number"], 42)
                self.assertEqual(json.loads(path.read_text())["phase"], "awaiting_validation")

    def test_draft_release_resumes_same_tag_after_deployment_failure(self):
        state = {"tags": [], "releases": [], "ref_writes": 0, "release_writes": 0}
        pr = dict(number=42, merged=True, base={"ref": "main"}, head={"ref": "release/v1.1.0", "sha": SHA, "repo": {"full_name": "o/r"}}, merge_commit_sha=MERGE,
                  title="chore: release v1.1.0", body="", html_url="https://github.com/o/r/pull/42")
        def remote(endpoint, method="GET", data=None):
            if endpoint.endswith("/pulls/42"):
                return pr
            if endpoint.endswith(f"/git/commits/{MERGE}"):
                return {"tree": {"sha": "tree"}, "parents": [{"sha": OTHER}, {"sha": SHA}]}
            if endpoint.endswith(f"/git/commits/{SHA}"):
                return {"tree": {"sha": "tree"}}
            if endpoint.endswith("/git/refs"):
                state["ref_writes"] += 1
                state["tags"].append({"name": "v1.1.0", "commit": {"sha": data["sha"]}})
                return {}
            if endpoint.endswith("/releases") and method == "POST":
                state["release_writes"] += 1
                value = {**data, "id": 7}
                state["releases"].append(value)
                return value
            if endpoint.endswith("/releases/7") and method == "PATCH":
                state["releases"][0].update(data)
                return state["releases"][0]
            raise AssertionError((endpoint, method))
        def lists(endpoint):
            return state["tags"] if endpoint.endswith("/tags") else state["releases"]
        with tempfile.TemporaryDirectory() as d:
            test_artifacts.Artifacts().bundle(d)
            def fetch(repo, evidence, target):
                target.mkdir()
                for name in ("manifest.json", "payload.tar.gz"):
                    shutil.copy2(Path(d) / name, target / name)
            # Fixture artifact repository differs deliberately from test API namespace.
            m = json.loads((Path(d) / "manifest.json").read_text())
            m["repository"] = "o/r"
            (Path(d) / "manifest.json").write_text(json.dumps(m))
            env = dict(GITHUB_REPOSITORY="o/r", GITHUB_SHA=MERGE, GITHUB_RUN_ID="99")
            with patch.dict(os.environ, env), patch("guardian.pipeline.config", return_value={}), patch("guardian.pipeline.api", side_effect=remote), patch("guardian.pipeline.pages", side_effect=lists), patch("guardian.pipeline.head", return_value=MERGE), patch("guardian.pipeline.protection_errors", return_value=[]), patch("guardian.pipeline.verify_version"), patch("guardian.pipeline.candidate", return_value={"artifact_id": 3, "run_id": 12, "run_url": "https://github.com/o/r/actions/runs/12"}), patch("guardian.pipeline.fetch_bundle", side_effect=fetch), patch("guardian.pipeline.deploy", side_effect=Blocked("health failed")):
                with self.assertRaisesRegex(Blocked, "health failed"):
                    pipeline.production(42)
            self.assertTrue(state["releases"][0]["draft"])
            with patch.dict(os.environ, env), patch("guardian.pipeline.config", return_value={}), patch("guardian.pipeline.api", side_effect=remote), patch("guardian.pipeline.pages", side_effect=lists), patch("guardian.pipeline.head", return_value=MERGE), patch("guardian.pipeline.protection_errors", return_value=[]), patch("guardian.pipeline.verify_version"), patch("guardian.pipeline.candidate", return_value={"artifact_id": 3, "run_id": 12}), patch("guardian.pipeline.fetch_bundle", side_effect=fetch), patch("guardian.pipeline.deploy", return_value=m) as deploy, patch("guardian.pipeline.gh"), patch("guardian.sync.synchronize", return_value={"status": "Ready"}):
                pipeline.production(42)
                self.assertEqual(deploy.call_count, 1)
                pipeline.production(42)
                self.assertEqual(deploy.call_count, 1)
            self.assertFalse(state["releases"][0]["draft"])
            self.assertEqual(state["ref_writes"], 1)
            self.assertEqual(state["release_writes"], 1)

    def test_wrong_release_number_blocked(self):
        pr = {"head": {"ref": "release/v99.0.0", "sha": SHA}}
        cfg = {"initial_version": "v0.1.0"}
        with patch("guardian.release.pages", return_value=[{"name": "v1.0.0"}]), patch("guardian.release.ancestry", return_value={"main_ancestor": True}), patch("guardian.release.changes_since", return_value=[{"message": "fix: checkout"}]):
            with self.assertRaisesRegex(Blocked, "v1.0.1"):
                release.verify_version("o/r", cfg, pr)

    def test_breaking_hotfix_not_published_as_patch(self):
        pr = {"head": {"ref": "hotfix/login", "sha": SHA}, "title": "fix!: replace API", "body": "", "labels": []}
        with self.assertRaisesRegex(Blocked, "normal release"):
            release.verify_version("o/r", {}, pr)
