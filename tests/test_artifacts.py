import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from support import SHA, OTHER
from guardian.core import Blocked
from guardian.pipeline import build, deployment_config, digest, health, unpack


class Artifacts(unittest.TestCase):
    def bundle(self, directory, members=None, identity=SHA):
        directory = Path(directory)
        archive = directory / "payload.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            for name, content, kind in (members or [("index.html", b"hello", "file"), ("guardian-release.json", json.dumps({"candidate_sha": identity}).encode(), "file")]):
                item = tarfile.TarInfo(name)
                if kind == "link":
                    item.type = tarfile.SYMTYPE
                    item.linkname = "/etc/passwd"
                    tar.addfile(item)
                else:
                    item.size = len(content)
                    tar.addfile(item, io.BytesIO(content))
        manifest = dict(schema=1, candidate_sha=SHA, sha256=digest(archive), repository="owner/repo", run_id=12)
        (directory / "manifest.json").write_text(json.dumps(manifest))
        return manifest

    def test_exact_artifact_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            manifest = self.bundle(d)
            unpack(d, Path(d) / "extract", SHA, "owner/repo", 12)
            self.assertEqual((Path(d) / "extract/index.html").read_text(), "hello")
            self.assertEqual(manifest["candidate_sha"], SHA)

    def test_tampered_payload(self):
        with tempfile.TemporaryDirectory() as d:
            self.bundle(d)
            with (Path(d) / "payload.tar.gz").open("ab") as f:
                f.write(b"tampered")
            with self.assertRaises(Blocked):
                unpack(d, Path(d) / "out", SHA, "owner/repo", 12)

    def test_foreign_repository(self):
        with tempfile.TemporaryDirectory() as d:
            self.bundle(d)
            with self.assertRaises(Blocked):
                unpack(d, Path(d) / "out", SHA, "attacker/repo", 12)

    def test_wrong_run(self):
        with tempfile.TemporaryDirectory() as d:
            self.bundle(d)
            with self.assertRaises(Blocked):
                unpack(d, Path(d) / "out", SHA, "owner/repo", 13)

    def test_traversal(self):
        with tempfile.TemporaryDirectory() as d:
            self.bundle(d, [("../outside.txt", b"bad", "file")])
            with self.assertRaises(Blocked):
                unpack(d, Path(d) / "out", SHA, "owner/repo", 12)
            self.assertFalse((Path(d) / "outside.txt").exists())

    def test_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            self.bundle(d, [("link", b"", "link")])
            with self.assertRaises(Blocked):
                unpack(d, Path(d) / "out", SHA, "owner/repo", 12)

    def test_marker_wrong_candidate(self):
        with tempfile.TemporaryDirectory() as d:
            self.bundle(d, identity=OTHER)
            with self.assertRaises(Blocked):
                unpack(d, Path(d) / "out", SHA, "owner/repo", 12)

    def test_duplicate_entries(self):
        with tempfile.TemporaryDirectory() as d:
            self.bundle(d, [("index.html", b"a", "file"), ("index.html", b"b", "file")])
            with self.assertRaises(Blocked):
                unpack(d, Path(d) / "out", SHA, "owner/repo", 12)

    def deployment(self):
        return {"deployment": {"provider": "aws-s3", "configured": True, "region": "us-east-1",
            "staging": {"bucket": "testing-bucket", "url": "https://test.example.com", "role_arn": "arn:aws:iam::123456789012:role/staging"},
            "production": {"bucket": "public-bucket", "url": "https://example.com", "role_arn": "arn:aws:iam::123456789012:role/production"}}}

    def test_valid_isolated_deployment(self):
        self.assertEqual(deployment_config(self.deployment(), "staging")[1], "us-east-1")

    def test_shared_bucket_rejected(self):
        cfg = self.deployment()
        cfg["deployment"]["production"]["bucket"] = "testing-bucket"
        with self.assertRaises(Blocked):
            deployment_config(cfg, "production")

    def test_shared_role_rejected(self):
        cfg = self.deployment()
        cfg["deployment"]["production"]["role_arn"] = cfg["deployment"]["staging"]["role_arn"]
        with self.assertRaises(Blocked):
            deployment_config(cfg, "production")

    def test_unsupported_provider(self):
        cfg = self.deployment()
        cfg["deployment"]["provider"] = "unimplemented-provider"
        with self.assertRaises(Blocked):
            deployment_config(cfg, "production")

    def test_failed_health_never_claims_success(self):
        with patch("guardian.pipeline.urllib.request.urlopen", side_effect=OSError), self.assertRaises(Blocked):
            health("https://example.invalid", SHA, attempts=1)

    def test_real_static_build(self):
        cfg = self.deployment()
        cfg.update(test_command=["python3", "-c", "assert 2 + 2 == 4"],
                   build_command=["python3", "-c", "from pathlib import Path; Path('dist').mkdir(); Path('dist/index.html').write_text('hello')"],
                   artifact_directory="dist")
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as d:
            try:
                os.chdir(d)
                env = dict(GITHUB_SHA=SHA, GITHUB_REPOSITORY="owner/repo", GITHUB_RUN_ID="12", RUNNER_TEMP=d, GITHUB_OUTPUT=str(Path(d) / "outputs"))
                with patch.dict(os.environ, env), patch("guardian.pipeline.config", return_value=cfg):
                    build()
                unpack(Path(d) / "guardian-bundle", Path(d) / "verified", SHA, "owner/repo", 12)
                self.assertEqual((Path(d) / "verified/index.html").read_text(), "hello")
            finally:
                os.chdir(previous)
