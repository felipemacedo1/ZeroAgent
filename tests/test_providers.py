import io
import json
import unittest
import urllib.error
from unittest.mock import MagicMock, patch

from zeroagent.providers import GroqAdapter, ProviderError, parse_edits


class ProviderTests(unittest.TestCase):
    def test_paid_and_unverified_block_before_network(self):
        with patch("urllib.request.build_opener") as network:
            for config in ({}, {"confirmed_free": False}, {"confirmed_free": "true"}):
                with self.assertRaises(ProviderError):
                    GroqAdapter(config)
        network.assert_not_called()

    def test_model_placeholder_blocked(self):
        with self.assertRaises(ProviderError):
            GroqAdapter({"confirmed_free": True, "model": "VERIFICAR NA DOCUMENTAÇÃO OFICIAL"})

    def test_schema(self):
        for content in ('{}', '[]', '{"edits": []}', '{"edits": {"a": 2}}', '{"edits": {}}'):
            with self.assertRaises(ProviderError):
                parse_edits(content)

    @patch.dict("os.environ", {"TEST_PROVIDER_KEY": "fake-unit-test-key"})
    @patch("urllib.request.build_opener")
    def test_real_adapter_contract_without_live_inference(self, opener):
        response = MagicMock()
        response.read.return_value = json.dumps({"choices": [{"finish_reason": "stop", "message": {
            "content": '{"edits":{"app.py":"print(1)"}}'}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5}}).encode()
        response.headers = {"x-ratelimit-remaining-requests": "2"}
        opener.return_value.open.return_value.__enter__.return_value = response
        adapter = GroqAdapter({"confirmed_free": True, "model": "test-model-not-a-real-id", "key_env": "TEST_PROVIDER_KEY"})
        result = adapter.generate("task", {"app.py": ""})
        self.assertEqual(result.input_tokens, 10)
        self.assertEqual(result.edits, {"app.py": "print(1)"})
        request = opener.return_value.open.call_args.args[0]
        payload = json.loads(request.data)
        self.assertFalse(payload["stream"])
        self.assertNotIn("fake-unit-test-key", json.dumps(payload))

    @patch.dict("os.environ", {"TEST_PROVIDER_KEY": "fake"})
    @patch("urllib.request.build_opener")
    def test_rate_limit_normalization(self, opener):
        opener.return_value.open.side_effect = urllib.error.HTTPError("https://example.invalid", 429,
            "limited", {"Retry-After": "12"}, io.BytesIO(b"private body"))
        adapter = GroqAdapter({"confirmed_free": True, "model": "test-only", "key_env": "TEST_PROVIDER_KEY"})
        with self.assertRaises(ProviderError) as caught:
            adapter.generate("task", {})
        self.assertEqual(str(caught.exception), "http_429")
        self.assertEqual(caught.exception.retry_after, "12")
