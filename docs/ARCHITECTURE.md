# Architecture

Issue → ephemeral local/Action runner → single Executor → constrained file edits
→ deterministic validation → TaskResult + Git patch → reviewable PR preparation.

The provider returns structured replacements, never shell commands. The operator
supplies allowed files and validation argv. Source is bounded, credentials and
runtime state are excluded. Docker validators have no network, dropped capabilities,
read-only root, resource limits, and only the task worktree mounted. Local trusted
validation is reserved for the bundled experiment; it is not a security sandbox.

SQLite stores integer micro-BRL budget reservations in BEGIN IMMEDIATE transactions.
Unknown/in-flight charges retain reservations across restart. Reservations are never
automatically released on timeout. Monthly accounting includes unresolved prior-month
reservations. An unexpected charge larger than its reservation is recorded and trips
a persistent paid-call block. One ledger must cover all paid activity.

v0.1 disables paid network calls, including Actions: ephemeral caches/artifacts cannot
serve as a globally authoritative financial ledger. v0.2 adds routing, capabilities,
call metrics, safe pricing bounds and durable accounting before enabling paid workers.
Streaming/tool calling are explicitly unsupported in the initial adapter. Structured
JSON is validated locally. No Validator/Coordinator/Consultant agents yet.
