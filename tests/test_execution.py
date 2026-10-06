import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from zeroagent.cli import BASE, IMPLEMENTATION, ACCEPTANCE, demo
from zeroagent.executor import execute, git, safe_file
from zeroagent.providers import MockProvider, ProviderError
from zeroagent.validators import CommandValidator


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def fixture(self):
        root = self.root / "repo"
        root.mkdir()
        (root / "app.py").write_text(BASE)
        git(root, "init", "-b", "main")
        git(root, "add", ".")
        git(root, "-c", "user.name=test", "-c", "user.email=test@localhost", "commit", "-m", "base")
        return root

    def run_task(self, edits, **kwargs):
        return execute(task_id="test", task="version", workspace=self.fixture(),
            allowed=["app.py"], commands=[ACCEPTANCE], provider=MockProvider(edits),
            artifacts=self.root / "artifacts", sandbox="trusted_fixture", **kwargs)

    def test_demo_produces_real_diff_and_checks(self):
        result = demo(self.root / "demo")
        self.assertEqual(result.status, "passed")
        self.assertEqual(set(result.files_changed), {"app.py", "test_app.py"})
        self.assertTrue(all(x["exit_code"] == 0 for x in result.validations))
        self.assertGreater(result.diff_stats["insertions"], 0)
        self.assertEqual(result.cost_brl, "0")
        self.assertEqual(result.tests, {"passed": 2, "failed": 0})
        saved = json.loads((self.root / "demo/artifacts/result.json").read_text())
        self.assertEqual(saved["status"], "passed")
        self.assertIn('--version', (self.root / "demo/artifacts/changes.patch").read_text())

    def test_model_cannot_claim_tests_pass(self):
        result = self.run_task({"app.py": 'print("tests passed")\n'})
        self.assertEqual(result.status, "failed")
        self.assertNotEqual(result.validations[0]["exit_code"], 0)
        self.assertFalse((self.root / "artifacts/PR.md").exists())

    def test_scope_prevalidated_before_write(self):
        result = self.run_task({"app.py": IMPLEMENTATION, "outside.py": "bad"})
        self.assertEqual(result.status, "blocked")
        self.assertEqual((self.root / "repo/app.py").read_text(), BASE)

    def test_dirty_repository_rejected(self):
        root = self.fixture()
        (root / "user.txt").write_text("keep")
        result = execute(task_id="t", task="t", workspace=root, allowed=["app.py"],
            commands=[ACCEPTANCE], provider=MockProvider({"app.py": IMPLEMENTATION}),
            artifacts=self.root / "artifacts", sandbox="trusted_fixture")
        self.assertEqual(result.attempts, 0)
        self.assertEqual((root / "user.txt").read_text(), "keep")

    def test_path_policy(self):
        for name in ("../x", "/tmp/x", ".env", "a/.git/config", "a/../b", "key.pem", "secrets.txt"):
            with self.assertRaises(ValueError):
                safe_file(self.root, name)
        (self.root / "link").symlink_to("/tmp", target_is_directory=True)
        with self.assertRaises(ValueError):
            safe_file(self.root, "link/x")
        (self.root / "a").write_text("x")
        os.link(self.root / "a", self.root / "b")
        with self.assertRaises(ValueError):
            safe_file(self.root, "b")

    def test_timeout_and_environment(self):
        validator = CommandValidator(sandbox="trusted_fixture", timeout=.1)
        result = validator.run(["python3", "-c", "import time; time.sleep(5)"], self.root)
        self.assertTrue(result.timed_out)
        self.assertEqual(result.exit_code, 124)
        with patch.dict(os.environ, {"SENSITIVE_TEST_KEY": "never-pass"}):
            result = CommandValidator(sandbox="trusted_fixture").run(
                ["python3", "-c", "import os; print(os.getenv('SENSITIVE_TEST_KEY'))"], self.root)
        self.assertEqual(result.stdout.strip(), "None")

    def test_shell_disallowed(self):
        with self.assertRaises(ValueError):
            CommandValidator().run(["sh", "-c", "echo no"], self.root)

    def test_429_persists_block_with_no_retry(self):
        with patch.object(MockProvider, "generate", side_effect=ProviderError("http_429", True, "60")) as call:
            result = self.run_task({"app.py": IMPLEMENTATION})
        self.assertEqual(call.call_count, 1)
        self.assertEqual(result.status, "blocked")
        self.assertEqual(result.retry_after, "60")
        self.assertEqual(json.loads((self.root / "artifacts/result.json").read_text())["failure"], "http_429")
