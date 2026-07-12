from __future__ import annotations

import unittest

from scripts.compact_guard import check, classify, protected_literals


class ClassifyTests(unittest.TestCase):
    def test_routine_status_is_compact_safe(self) -> None:
        result = classify("Build passed. Two files changed. No blocker remains.")
        self.assertEqual(result["mode"], "compact-safe")

    def test_destructive_command_requires_full_prose(self) -> None:
        result = classify("Run `git reset --hard` before deploying to production.")
        self.assertEqual(result["mode"], "full-prose")
        self.assertIn("destructive-or-irreversible", result["reasons"])

    def test_descriptive_before_does_not_trigger_ordered_procedure(self) -> None:
        result = classify("Reject expired tokens before attempting a database write.")
        self.assertEqual(result["mode"], "compact-safe")

    def test_procedural_before_requires_full_prose(self) -> None:
        result = classify("Before changing the schema, create a verified backup.")
        self.assertEqual(result["mode"], "full-prose")
        self.assertIn("ordered-procedure", result["reasons"])


class CheckTests(unittest.TestCase):
    def test_path_does_not_absorb_following_prose(self) -> None:
        literals = protected_literals("Use /tmp/project. Then continue.")
        self.assertEqual(list(literals["path"].elements()), ["/tmp/project"])

    def test_preserved_literals_pass(self) -> None:
        source = "Run `pytest -q` against /tmp/project. Do not use `--force`."
        candidate = "Run `pytest -q` in /tmp/project. Do not use `--force`."
        self.assertTrue(check(source, candidate)["ok"])

    def test_coordinated_negation_passes(self) -> None:
        source = "Do not use `--force`, and do not remove `/tmp/backup`."
        candidate = "Do not use `--force` or remove `/tmp/backup`."
        self.assertTrue(check(source, candidate)["ok"])

    def test_missing_literal_and_negation_fail(self) -> None:
        source = "Do not run `rm -rf /tmp/project`."
        candidate = "Run cleanup."
        result = check(source, candidate)
        self.assertFalse(result["ok"])
        kinds = {item["kind"] for item in result["missing"]}
        self.assertIn("inline-code", kinds)
        self.assertIn("negation", kinds)


if __name__ == "__main__":
    unittest.main()
