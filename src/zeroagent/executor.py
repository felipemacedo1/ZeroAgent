"""Single bounded attempt; evidence is produced by processes, not the model."""
import json
import os
import re
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath

from .providers import ProviderAdapter, ProviderError
from .validators import CommandValidator


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-c", "core.hooksPath=/dev/null", *args],
        cwd=root, check=True, capture_output=True, text=True, timeout=30,
        env={"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8",
             "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null"})
    return result.stdout.strip()


def safe_file(root: Path, name: str) -> Path:
    path = PurePosixPath(name)
    if (not name or path.is_absolute() or ".." in path.parts or "\\" in name
            or any(part.startswith(".") for part in path.parts)
            or path.as_posix() != name or path.suffix in {".pem", ".key", ".sqlite"}
            or any(word in name.lower() for word in ("secret", "credential"))):
        raise ValueError("Unsafe or sensitive file path")
    resolved = root / name
    if not resolved.resolve().is_relative_to(root.resolve()):
        raise ValueError("Path escapes workspace")
    for item in [resolved, *resolved.parents]:
        if item == root:
            break
        if item.is_symlink():
            raise ValueError("Symlinks not allowed")
    if resolved.exists() and (not resolved.is_file() or resolved.stat().st_nlink != 1):
        raise ValueError("Not an ordinary single-link file")
    return resolved


@dataclass
class TaskResult:
    task_id: str
    status: str = "blocked"
    files_changed: list[str] = field(default_factory=list)
    tests: dict = field(default_factory=lambda: {"passed": None, "failed": None})
    failure: str | None = None
    attempts: int = 0
    diff_stats: dict = field(default_factory=lambda: {"insertions": 0, "deletions": 0})
    validations: list = field(default_factory=list)
    provider: str | None = None
    model: str | None = None
    tokens: dict = field(default_factory=dict)
    cost_brl: str = "0"
    duration: float = 0
    branch: str | None = None
    base_commit: str | None = None
    artifacts: list[str] = field(default_factory=list)
    retry_after: str | None = None


def execute(*, task_id: str, task: str, workspace: Path, allowed: list[str],
            commands: list[list[str]], provider: ProviderAdapter, artifacts: Path,
            sandbox: str = "docker") -> TaskResult:
    result = TaskResult(task_id)
    start = time.monotonic()
    workspace = workspace.resolve()
    artifacts = artifacts.resolve()
    if artifacts.is_relative_to(workspace):
        raise ValueError("Artifacts must be outside task worktree")
    artifacts.mkdir(parents=True, exist_ok=False)
    try:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", task_id):
            raise ValueError("Invalid task ID")
        if not allowed or len(allowed) > 20 or not commands or len(commands) > 10:
            raise ValueError("Require bounded file scope and validation commands")
        if sandbox == "trusted_fixture" and provider.__class__.__name__ != "MockProvider":
            raise ValueError("Real providers require Docker")
        if git(workspace, "status", "--porcelain", "--untracked-files=all"):
            raise ValueError("Workspace must be clean")
        result.base_commit = git(workspace, "rev-parse", "HEAD")
        result.branch = f"zeroagent/{task_id}"
        paths = {name: safe_file(workspace, name) for name in allowed}
        files = {name: p.read_text() if p.exists() else "" for name, p in paths.items()}
        if sum(len(v.encode()) for v in files.values()) + len(task.encode()) > 60_000:
            raise ValueError("Task context too large")
        git(workspace, "switch", "-c", result.branch)
        result.attempts = 1
        response = provider.generate(task, files)
        result.provider, result.model = response.provider, response.model
        result.cost_brl = response.cost_brl
        result.tokens = {"input": response.input_tokens, "output": response.output_tokens,
                         "cached": response.cached_tokens}
        if not response.edits or not set(response.edits) <= set(allowed):
            raise ValueError("Provider exceeded allowed file scope")
        # Validate the complete set before applying any edit.
        for name, content in response.edits.items():
            safe_file(workspace, name)
            if not isinstance(content, str) or len(content.encode()) > 100_000:
                raise ValueError("Invalid replacement")
        for name, content in response.edits.items():
            paths[name].parent.mkdir(parents=True, exist_ok=True)
            paths[name].write_text(content)
        git(workspace, "add", "--", *response.edits)
        result.files_changed = git(workspace, "diff", "--cached", "--name-only").splitlines()
        if not result.files_changed:
            raise ValueError("No change produced")
        git(workspace, "diff", "--cached", "--check")
        validator = CommandValidator(sandbox=sandbox)
        for command in commands:
            result.validations.append(asdict(validator.run(command, workspace)))
        counted = [v for v in result.validations if v["tests_passed"] is not None]
        if counted:
            result.tests = {"passed": sum(v["tests_passed"] for v in counted),
                            "failed": sum(v["tests_failed"] for v in counted)}
        result.status = "passed" if all(v["exit_code"] == 0 for v in result.validations) else "failed"
        if result.status == "failed":
            result.failure = "deterministic_validation_failed"
        for line in git(workspace, "diff", "--cached", "--numstat").splitlines():
            added, deleted, _ = line.split("\t", 2)
            if added.isdigit():
                result.diff_stats["insertions"] += int(added)
                result.diff_stats["deletions"] += int(deleted)
        patch = artifacts / "changes.patch"
        patch.write_text(git(workspace, "diff", "--cached", "--binary") + "\n")
        result.artifacts.append(str(patch))
        if result.status == "passed":
            pr = artifacts / "PR.md"
            pr.write_text(f"# Task {task_id}\n\nDeterministic checks passed. Review attached patch.\n"
                          f"\nBase: {result.base_commit}\nBranch: {result.branch}\n"
                          f"\nProvider: {result.provider}/{result.model}; cost BRL {result.cost_brl}.\n")
            result.artifacts.append(str(pr))
    except ProviderError as exc:
        result.failure = exc.kind
        result.retry_after = exc.retry_after
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        # Avoid serializing subprocess output, request headers or credentials.
        result.failure = f"{type(exc).__name__}: operation blocked or failed"
    result.duration = time.monotonic() - start
    target = artifacts / "result.json"
    temp = artifacts / "result.json.tmp"
    temp.write_text(json.dumps(asdict(result), indent=2) + "\n")
    os.replace(temp, target)
    return result
