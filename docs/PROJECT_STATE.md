# Project state

Version: v0.1.0 development candidate (not a released/fully qualified milestone).
Milestone: v0.1.0. Current Issue: #1. Experiment: #7. Review: PR #8.

Completed: CLI/install, mock and configurable Groq adapter, single bounded Executor,
file policy, Docker deterministic validator, structured TaskResult, Git patch/PR
preparation, transactional integer budget ledger, hard stop and safety margin tests,
concurrency/reconciliation/restart tests, workflows and contribution documentation.
25 tests pass locally with actual Docker integration. Local and Docker experiments
pass 2 tests plus independent acceptance, 1 attempt, no retries, zero inference cost.
GitHub CI and Issue experiment succeeded on the initial implementation; exact current
PR-head checks are authoritative on GitHub. No live model inference performed.

GitHub source of management: https://github.com/felipemacedo1/ZeroAgent . Milestones
v0.1 through v1.0 and roadmap Issues #2–#6 exist. Projects blocked by token scopes (#9).
Real-provider proof blocked by verified free account/model and credential setup (#10).
Next: review PR #8; complete #10 before claiming real-model v0.1 success. #2 contains
the next implementation milestone once the single-Executor evidence gate is satisfied.

Known limitations: paid network calls are disabled, budget ledger is not an ephemeral
worker billing solution, no automatic PR publishing/merging, no dynamic router or
Capability DB yet, 429 is persisted as blocked without immediate retry (backoff/fallback
in v0.2), no generalized task crash recovery/idempotency yet. Streaming/tool calls are
explicitly unsupported. Only budget reservations have conservative crash persistence.
Risk: mock correctness says nothing about real model quality. Generic test counts may
be unknown; process exit codes determine status. No release or multi-agent claim.
Open decisions: actual free model, durable paid ledger design, benchmark corpus.
