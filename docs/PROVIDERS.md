# Provider registry

Verified documentation date: 2026-10-06. No model is selected by default.

| Adapter | Endpoint/auth | Evidence | Status |
|---|---|---|---|
| mock | local, no auth | repository fixture | verified, zero cost |
| groq | https://api.groq.com/openai/v1/chat/completions ; Bearer environment key | https://console.groq.com/docs/api-reference | endpoint/auth verified; live calls untested |

Groq model IDs, account eligibility in Brazil, free quotas, input/output pricing,
cache pricing, context sizes and per-model structured-output compatibility:
**VERIFICAR NA DOCUMENTAÇÃO OFICIAL**. https://console.groq.com/docs/structured-outputs
and https://console.groq.com/docs/rate-limits . Do not infer free status from an alias.
Initial adapter uses non-streaming text JSON; tools/streaming are unsupported.
HTTP 429 becomes a typed retryable event; no automatic retries/bypass in v0.1.

GitHub standard hosted runners for public repositories are documented as free:
https://docs.github.com/en/billing/concepts/product-billing/github-actions .
Artifacts/cache have separate storage accounting. Workers terminate; no cron/VPS.
Account eligibility and actual CI execution must be verified independently.

## Controlled live experiment (2026-10-06)

Operator confirmed the organization is on Free with no usage billing enabled.
GitHub secret GROQ_API_KEY is provisioned; its value is never read back or logged.
Alias free_executor_a in config.groq.json selects openai/gpt-oss-20b, currently listed
at https://console.groq.com/docs/rate-limits and https://console.groq.com/docs/models .
The authenticated GET /openai/v1/models preflight checks current model availability;
it does not establish billing status. The repository variable
GROQ_FREE_ACCOUNT_CONFIRMED records the operator confirmation separately from the key.
One completion per live workflow, max 4096 output tokens; no automatic retry.
Other accounts must verify their own plan. Published quotas are not a reservation.
