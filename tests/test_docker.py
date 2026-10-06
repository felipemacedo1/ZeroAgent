"""Opt-in real-container isolation evidence, enabled in CI."""
import os
import tempfile
import unittest
from pathlib import Path

from zeroagent.validators import CommandValidator


@unittest.skipUnless(os.environ.get("ZEROAGENT_DOCKER_TESTS") == "1", "enable Docker integration explicitly")
class DockerTests(unittest.TestCase):
    def test_read_only_network_disabled_environment_restricted(self):
        code = '''import os, socket
assert "SENSITIVE_TEST_KEY" not in os.environ
try:
    open("/work/forbidden", "w")
except OSError:
    pass
else:
    raise AssertionError("workspace writable")
s = socket.socket()
s.settimeout(1)
try:
    s.connect(("1.1.1.1", 443))
except OSError:
    pass
else:
    raise AssertionError("network reachable")
print("isolation verified")
'''
        with tempfile.TemporaryDirectory() as directory:
            result = CommandValidator().run(["python3", "-c", code], Path(directory))
            self.assertEqual(result.exit_code, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "isolation verified")
