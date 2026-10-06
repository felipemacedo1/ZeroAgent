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

## Configured provider experiment

After verifying a real model and an account with paid billing disabled, replace the
placeholder in `config.example.yaml`, explicitly set `confirmed_free` to `true`, and
export the key named by `key_env`. JSON configuration is a YAML subset; arbitrary YAML
syntax is not parsed. Do not place credentials in the task checkout.

```sh
docker pull python:3.12-slim
zeroagent run --task examples/task.json --workspace /path/to/clean/task-checkout \
  --artifacts /path/to/new/artifacts --config config.example.yaml --alias free_executor_a
```

The example expects `app.py` in a dedicated clean Git checkout. Run operates on that
checkout and creates a task branch; it refuses dirty worktrees and existing branches.
Pass only explicitly reviewed source paths; secret detection is not a general DLP
guarantee. Commands are operator input, never model output. Inspect `changes.patch`,
`result.json` and `PR.md` before committing/publishing the generated change.
