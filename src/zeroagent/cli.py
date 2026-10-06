import argparse
import json
from dataclasses import asdict
from pathlib import Path

from . import __version__
from .executor import execute, git
from .providers import GroqAdapter, MockProvider

BASE = 'import argparse\n\np = argparse.ArgumentParser()\np.parse_args()\nprint("hello")\n'
IMPLEMENTATION = BASE.replace('p.parse_args()', 'p.add_argument("--version", action="version", version="sample 0.1.0")\np.parse_args()')
TEST = '''import subprocess
import unittest

class VersionTest(unittest.TestCase):
    def test_version(self):
        result = subprocess.run(["python3", "app.py", "--version"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "sample 0.1.0")

    def test_default(self):
        result = subprocess.run(["python3", "app.py"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "hello")

if __name__ == "__main__":
    unittest.main()
'''
# Independent acceptance is supplied by the operator, not by the model's own tests.
ACCEPTANCE = ['python3', '-c', 'import subprocess; r=subprocess.run(["python3","app.py","--version"],capture_output=True,text=True); assert r.returncode == 0 and r.stdout.strip() == "sample 0.1.0"; r=subprocess.run(["python3","app.py"],capture_output=True,text=True); assert r.returncode == 0 and r.stdout.strip() == "hello"']


def demo(root: Path, sandbox="trusted_fixture", issue=None, provider=None):
    root.mkdir(parents=True, exist_ok=False)
    worktree = root / "repo"
    worktree.mkdir()
    (worktree / "app.py").write_text(BASE)
    git(worktree, "init", "-b", "main")
    git(worktree, "add", "app.py")
    git(worktree, "-c", "user.name=ZeroAgent", "-c", "user.email=zeroagent@localhost",
        "commit", "-m", "fixture: initial CLI")
    task_id = f"issue-{issue['number']}" if issue else "version"
    description = f"{issue['title']}\n{issue['body']}" if issue else "Add --version and tests to the sample CLI"
    return execute(task_id=task_id, task=description,
        workspace=worktree, allowed=["app.py", "test_app.py"],
        commands=[["python3", "-m", "unittest", "discover", "-v"], ACCEPTANCE],
        provider=provider or MockProvider({"app.py": IMPLEMENTATION, "test_app.py": TEST}),
        artifacts=root / "artifacts", sandbox=sandbox)


def main():
    parser = argparse.ArgumentParser(prog="zeroagent")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    example = sub.add_parser("demo", help="Run the bundled zero-cost mock experiment")
    example.add_argument("--root", type=Path, required=True)
    example.add_argument("--sandbox", choices=["trusted_fixture", "docker"], default="trusted_fixture")
    example.add_argument("--issue-json", type=Path, help="Associate the bundled experiment with a fetched GitHub Issue")
    run = sub.add_parser("run", help="Run a task JSON against a clean isolated Git checkout (Docker required)")
    run.add_argument("--task", type=Path, required=True)
    run.add_argument("--workspace", type=Path, required=True)
    run.add_argument("--artifacts", type=Path, required=True)
    run.add_argument("--config", type=Path, required=True, help="JSON config (also valid YAML)")
    run.add_argument("--alias", required=True)
    args = parser.parse_args()
    if args.command == "demo":
        result = demo(args.root, args.sandbox, json.loads(args.issue_json.read_text()) if args.issue_json else None)
    else:
        task = json.loads(args.task.read_text())
        config = json.loads(args.config.read_text())["aliases"][args.alias]
        if config.get("adapter") != "groq":
            parser.error("Unsupported adapter")
        result = execute(task_id=task["task_id"], task=task["description"],
            workspace=args.workspace, allowed=task["allowed_files"],
            commands=task["commands"], provider=GroqAdapter(config), artifacts=args.artifacts)
    print(json.dumps(asdict(result), indent=2))
    return 0 if result.status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
