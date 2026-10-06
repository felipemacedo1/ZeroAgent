# ZeroAgent

Event-driven software engineering with one Executor and deterministic evidence.
Operational target: R$0–10/month; absolute paid inference ceiling: R$50/month.
No GitHub Models, permanent workers, or multi-agent default.

## Run the zero-cost experiment

```sh
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/zeroagent demo --root workspace/demo
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

The demo creates a tiny Git CLI project, applies a mock Executor response adding
`--version`, runs independent acceptance checks, and saves TaskResult and a patch.
Mock success proves the machinery, **not LLM coding quality**. No key is needed.
Use `--sandbox docker` to execute checks in a network-disabled container (requires
the `python:3.12-slim` image locally). The local trusted mode is only for this
bundled fixture. General tasks require Docker isolation.

`zeroagent run --help` describes the configurable real-provider path. Real calls
are disabled unless the operator explicitly confirms a free account configuration.
Paid transport is intentionally disabled in v0.1 until conservative token-bound
estimation and shared durable worker accounting are implemented. The transactional
budget ledger is implemented and tested independently, never a promise in `.env`.

See [architecture](docs/ARCHITECTURE.md), [state](docs/PROJECT_STATE.md),
[providers](docs/PROVIDERS.md), and [handoff](docs/HANDOFF.md).
