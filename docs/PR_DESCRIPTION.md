Adds a single-Executor task pipeline that turns a constrained file-edit response into
a real Git diff, runs deterministic checks, and emits TaskResult plus PR preparation
artifacts. The bundled version-flag experiment succeeds locally and inside Docker
without inference calls. Ref #1 and #7.

Includes a configurable Groq adapter, explicit free-account gate, integer micro-BRL
SQLite budget reservations/reconciliation, hard ceiling, concurrency control and
conservative recovery of ambiguous charges. Paid transport remains disabled until
verified pricing bounds and durable cross-worker accounting are available.

Validation: 25 unittest tests with Docker integration enabled; local and Docker mock
experiments each pass two tests and independent acceptance; editable install and CLI
version check pass. No real-provider inference was performed. The workflow generates
reviewable patch artifacts; it does not autonomously merge or publish task changes.

Roadmap issues and milestones exist through v1.0. Projects integration is blocked by
missing token scopes. Dynamic router, Capability DB and further agent roles are later
milestones and are not represented as implemented here.
