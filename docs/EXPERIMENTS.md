# Experiment 001 — version flag

Date: 2026-10-06. GitHub Issue: #7. Provider: mock/fixture (no network inference).
Task: add `--version` printing `sample 0.1.0`, preserve `hello`, add unittest tests.
Allowed changes: app.py, test_app.py in a disposable Git repository.

Observed local trusted execution: passed on first attempt, 2 tests passed, 0 failed,
plus an independent acceptance command. 17 insertions, 0 deletions. 0 input/output/
cached tokens, R$0 inference, no retries or escalation. Local duration ~0.25 seconds
(machine-specific). Human intervention: fixture and acceptance authored by developer.

Docker execution also passed: 2/2 tests and independent acceptance, ~1.25 seconds.
Separate integration test verifies read-only worktree and network denial.

GitHub-hosted execution fetched Issue #7 and passed the same Docker checks:
https://github.com/felipemacedo1/ZeroAgent/actions/runs/37519331537 . The workflow
is activated by PR events or manual dispatch, reads Issue text as data, and produces
patch/PR-preparation artifacts. It does not watch all new Issues or publish a task PR.

This establishes task plumbing, bounded edits, test execution, structured evidence and
patch preparation. It does not establish Issue comprehension, coding ability of a
real model, multi-agent advantage, production security, or paid cost per correct task.
Real-provider comparison requires an explicitly verified free account/model; no
inference keys were searched for or used in this experiment.

Runtime artifacts are ignored under workspace/{local,docker}/artifacts. CI uploads
results for one day; durable source includes test fixtures and reproducible commands.
