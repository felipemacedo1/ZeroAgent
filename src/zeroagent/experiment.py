"""Explicit real-provider experiment, with a non-inference credential preflight."""
import argparse
import json
import os
import urllib.error
import urllib.request
from dataclasses import asdict
from pathlib import Path

from .cli import demo
from .providers import GroqAdapter, NoRedirect, ProviderError


def list_models():
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise ProviderError("missing_credential")
    request = urllib.request.Request("https://api.groq.com/openai/v1/models",
        headers={"Authorization": f"Bearer {key}", "User-Agent": "ZeroAgent/0.1.0",
                 "Accept": "application/json"})
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=30) as response:
            raw = response.read(200001)
            if len(raw) > 200000:
                raise ProviderError("response_too_large")
            data = json.loads(raw)
            return sorted(item["id"] for item in data["data"] if item.get("active", True))
    except urllib.error.HTTPError as exc:
        # Only a bounded error category; never emit headers, key, or raw error body.
        raw = exc.read(4096).decode(errors="replace")
        category = "non_json_error"
        try:
            error = json.loads(raw).get("error", {})
            category = str(error.get("type", "unknown"))
        except (ValueError, AttributeError):
            pass
        print(json.dumps({"http_status": exc.code, "error_category": category.replace(key, "[redacted]")[:80]}))
        raise ProviderError(f"http_{exc.code}") from None
    except (OSError, ValueError, KeyError, TypeError):
        raise ProviderError("preflight_unavailable_or_invalid") from None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--root", type=Path, default=Path("workspace/live"))
    parser.add_argument("--issue-json", type=Path)
    parser.add_argument("--config", type=Path, default=Path("config.groq.json"))
    parser.add_argument("--alias", default="free_executor_a")
    args = parser.parse_args()
    try:
        models = list_models()
        print(json.dumps({"authentication": "passed", "available_models": models,
                          "inference_calls": 0, "account_plan": "not_exposed_by_models_api"}))
        if args.preflight:
            return 0
        config = json.loads(args.config.read_text())["aliases"][args.alias]
        if os.environ.get("GROQ_FREE_ACCOUNT_CONFIRMED") != "true":
            raise ProviderError("free_account_confirmation_required")
        if config["model"] not in models:
            raise ProviderError("configured_model_unavailable")
        config["confirmed_free"] = True
        provider = GroqAdapter(config)
        issue = json.loads(args.issue_json.read_text()) if args.issue_json else None
        result = demo(args.root, "docker", issue, provider)
        print(json.dumps(asdict(result), indent=2))
        return 0 if result.status == "passed" else 1
    except ProviderError as exc:
        print(json.dumps({"status": "blocked", "reason": exc.kind}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
