# Decisions

## ADR-001 — Prove one zero-cost vertical slice (2026-10-06)
Context: an empty repository and a strict R$50 ceiling.
Decision: Python standard library, SQLite, one Executor, JSON replacements, mock demo.
Alternatives: SDK framework, agent teams, paid inference from day one.
Consequences: small reproducible runtime; model usefulness remains unmeasured.

## ADR-002 — Fail closed on paid transport
Context: provider prices/account quotas are unverified and Actions disks ephemeral.
Decision: implement/test ledger now, disable paid transport until safe upper bounds
and durable cross-worker state exist. Free status requires explicit operator config.
Alternatives: trust estimated costs or restore a cache as the ledger.
Consequences: no paid call can exceed the ceiling in v0.1; paid execution deferred.

## ADR-003 — Controlled execution
Context: model-produced code is untrusted even with argv allowlisting.
Decision: Docker for general-task validation; trusted host mode only for mock demo.
Alternatives: shell blacklists alone, host subprocess for arbitrary projects.
Consequences: Docker/image needed for real tasks; no network during validation.
