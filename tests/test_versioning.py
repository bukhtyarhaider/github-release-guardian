import unittest
from support import SHA
from guardian.core import Blocked
from guardian.policy import calculate, impact, version, version_key


class Versioning(unittest.TestCase):
    def next(self, message, **kwargs):
        return calculate("v1.4.2", [{"message": message}], **kwargs)["version"]

    def test_patch(self):
        self.assertEqual(self.next("fix: repair checkout"), "v1.4.3")

    def test_minor(self):
        self.assertEqual(self.next("feat: add login"), "v1.5.0")

    def test_bang_major(self):
        self.assertEqual(self.next("feat(api)!: change login"), "v2.0.0")

    def test_body_breaking_major(self):
        self.assertEqual(self.next("fix: update\n\nBREAKING CHANGE: old clients must migrate"), "v2.0.0")

    def test_breaking_wins_patch_label(self):
        self.assertEqual(impact({"message": "fix!: incompatible", "labels": ["release:patch"]}), "major")

    def test_label_priority(self):
        self.assertEqual(impact({"message": "Fix checkout", "labels": ["release:patch", "release:minor"]}), "minor")

    def test_none_conflict(self):
        with self.assertRaises(Blocked):
            impact({"message": "feat: login", "labels": ["release:none"]})

    def test_unknown_requires_question(self):
        with self.assertRaisesRegex(Blocked, "version choice"):
            self.next("Update stuff")

    def test_no_release_for_docs(self):
        with self.assertRaises(Blocked):
            self.next("docs: update guide")

    def test_duplicate_blocked(self):
        with self.assertRaisesRegex(Blocked, "already exists"):
            self.next("fix: repair", existing=["v1.4.3"])

    def test_initial(self):
        self.assertEqual(calculate(None, [{"message": "feat: first"}])["version"], "v0.1.0")

    def test_non_semver_needs_baseline(self):
        with self.assertRaises(Blocked):
            calculate("build-123", [{"message": "fix: repair"}])

    def test_prerelease_increment(self):
        self.assertEqual(self.next("feat: login", prerelease="rc", existing=["v1.5.0-rc.1"]), "v1.5.0-rc.2")

    def test_prerelease_to_stable(self):
        self.assertEqual(calculate("v1.5.0-rc.2", [{"message": "feat: login"}])["version"], "v1.5.0")

    def test_numeric_ordering(self):
        self.assertGreater(version_key("v1.10.0"), version_key("v1.9.9"))
        self.assertGreater(version_key("v1.0.0-rc.10"), version_key("v1.0.0-rc.2"))
        self.assertGreater(version_key("v1.0.0"), version_key("v1.0.0-rc.10"))

    def test_invalid_versions(self):
        for tag in ("v01.0.0", "1.2", "v1.0.0-01", "v1.0.0+build", "v1.0.0-"):
            with self.subTest(tag=tag), self.assertRaises(Blocked):
                version(tag)
