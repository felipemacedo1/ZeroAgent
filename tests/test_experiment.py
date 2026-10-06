import json
import unittest
from unittest.mock import MagicMock, patch

from zeroagent.experiment import list_models, main
from zeroagent.providers import ProviderError


class ExperimentTests(unittest.TestCase):
    @patch.dict('os.environ', {}, clear=True)
    def test_no_key_no_request(self):
        with patch('urllib.request.build_opener') as network:
            with self.assertRaises(ProviderError):
                list_models()
            network.assert_not_called()

    @patch.dict('os.environ', {'GROQ_API_KEY': 'test-only'})
    @patch('urllib.request.build_opener')
    def test_models_preflight_only_get(self, opener):
        response = MagicMock()
        response.read.return_value = json.dumps({'data': [{'id': 'test-model', 'active': True}]}).encode()
        opener.return_value.open.return_value.__enter__.return_value = response
        self.assertEqual(list_models(), ['test-model'])
        request = opener.return_value.open.call_args.args[0]
        self.assertEqual(request.get_method(), 'GET')
        self.assertTrue(request.full_url.endswith('/models'))

    @patch.dict('os.environ', {}, clear=True)
    @patch('zeroagent.experiment.list_models', return_value=['openai/gpt-oss-20b'])
    @patch('sys.argv', ['experiment'])
    def test_unconfirmed_account_never_generates(self, models):
        with patch('zeroagent.experiment.GroqAdapter') as adapter:
            self.assertEqual(main(), 1)
            adapter.assert_not_called()
