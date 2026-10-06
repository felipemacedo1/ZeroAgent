"""Operator-defined argv, bounded output and process-group timeouts."""
import os
import re
import resource
import signal
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass
class ValidationResult:
    command: list[str]
    exit_code: int
    duration: float
    stdout: str
    stderr: str
    timed_out: bool = False
    # Generic commands do not imply a known test count.
    tests_passed: int | None = None
    tests_failed: int | None = None


class DeterministicValidator(Protocol):
    def run(self, command: list[str], workspace: Path) -> ValidationResult: ...


def output_limit():
    # Bound disk consumption as well as the prompt excerpt. Linux runner contract.
    resource.setrlimit(resource.RLIMIT_FSIZE, (1_048_576, 1_048_576))


class CommandValidator:
    def __init__(self, *, sandbox="docker", timeout=60):
        if sandbox not in {"docker", "trusted_fixture"}:
            raise ValueError("Unknown sandbox")
        self.sandbox, self.timeout = sandbox, timeout

    def run(self, command, workspace):
        if not command or command[0] not in {"python3", "pytest", "ruff", "mypy"}:
            raise ValueError("Command executable not allowed")
        if any(not isinstance(arg, str) or "\x00" in arg for arg in command):
            raise ValueError("Invalid argv")
        argv = command
        container = "zeroagent-" + uuid.uuid4().hex
        if self.sandbox == "docker":
            argv = ["docker", "run", "--rm", "--pull=never", "--name", container,
                "--network=none", "--read-only", "--cap-drop=ALL",
                "--security-opt=no-new-privileges", "--pids-limit=64", "--memory=256m",
                "--cpus=1", "--ulimit", "fsize=1024:1024",
                "--user", f"{os.getuid()}:{os.getgid()}",
                "--tmpfs", "/tmp:rw,noexec,nosuid,size=32m",
                "--mount", f"type=bind,src={workspace.resolve()},dst=/work,readonly",
                "--workdir", "/work", "--env", "PYTHONDONTWRITEBYTECODE=1",
                "python:3.12-slim", *command]
        env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8",
               "PYTHONDONTWRITEBYTECODE": "1"}
        start = time.monotonic()
        timed_out = False
        with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
            process = subprocess.Popen(argv, cwd=workspace, env=env, stdout=out,
                                       stderr=err, start_new_session=True,
                                       preexec_fn=output_limit)
            try:
                process.wait(timeout=self.timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            finally:
                if self.sandbox == "docker":
                    subprocess.run(["docker", "rm", "-f", container], env=env,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
            out.seek(0)
            err.seek(0)
            stdout = out.read(4096).decode(errors="replace")
            stderr = err.read(4096).decode(errors="replace")
            result = ValidationResult(command, 124 if timed_out else process.returncode,
                time.monotonic() - start, stdout, stderr, timed_out)
            # Counts are advisory parsed evidence; exit status remains authoritative.
            count = re.search(r"Ran (\d+) tests? in", stderr)
            if count and not timed_out:
                failures = re.search(r"FAILED \(([^)]+)\)", stderr)
                skipped = sum(int(n) for n in re.findall(r"skipped=(\d+)", stderr))
                failed = sum(int(n) for n in re.findall(r"(?:failures|errors)=(\d+)", failures[1])) if failures else 0
                if failures or re.search(r"^OK(?:\s|$)", stderr, re.MULTILINE):
                    result.tests_failed = failed
                    result.tests_passed = max(0, int(count[1]) - failed - skipped)
            return result
