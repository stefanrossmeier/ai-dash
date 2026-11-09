# X report correction and acceptance status

The initial implementation was pushed first as commit `bfaa63c` so it could be
inspected before this separate correction. The X schedule remains disabled.

## Observed failure

The one user-authorized paid verification cost $1.03470405. Its provider trace
reported 18 search queries, including accounts outside the intended three, and
returned zero structured posts. A successful HTTP request did not establish a
working source-restricted report. The normal daily budget was not reset.

## Corrections

- An ai-dash-owned X provider boundary replaces the shared daily-dash X endpoint.
  The shared cheap ranking gateway remains unchanged.
- The request names the actual accounts in the prompt as well as the native X
  allowlist. It supplies a single combined `from:` query and permits no followups.
- `max_tool_calls: 1`, `max_total_results: 6`, and `max_output_tokens: 1200` bound
  the request. Provider routing is pinned to xAI, with no fallback or retry.
- Today's UTC posts are included by using tomorrow as the exclusive date end.
  Application code still enforces the exact rolling 24-hour timestamp boundary.
- Provider responses must contain exactly one auditable search, the exact allowed
  author set and date range, valid structured posts and matching citation evidence.
  Unexpected searches, unrelated authors, missing audit evidence and incomplete
  responses fail instead of masquerading as quiet days.
- Unverified legacy caches are refused without another paid request. The provider
  service reserves its own daily allowance before calling OpenRouter, in addition
  to the existing application-level budget. Failed responses are quarantined.
- `x_major.enabled: false` is respected even by workspace registration with `--enable`.

The provider's internal billing still depends on fetched items and tokens. These
limits do not promise an exact dollar ceiling. A post-response audit cannot undo
a provider charge, which is why reactivation requires a real paid acceptance test.

## Validation completed without additional paid requests

The automated suite covers outgoing request bounds, inclusive-current-day range,
valid/quiet results, author/citation/query/date failures, the 18-query failure shape,
one paid attempt across repeated service calls, zero-cost cache reuse, and health
checks that do not contact a provider. Existing delivery/history tests also pass.

The deployed `/health` check validates service startup and routing only. It does
not verify actual provider behavior. No second paid verification has been made.
The X schedule must stay paused until the user authorizes that final test and it
succeeds. The company, blog and research/open-source reports continue operating.

## Primary documentation consulted

- [OpenRouter X search parameters and result/search budgets](https://openrouter.ai/docs/guides/features/server-tools/web-search)
- [OpenRouter server-tool step budget](https://openrouter.ai/docs/guides/features/server-tools#tool-call-limits)
- [xAI exclusive date-end semantics and native account filters](https://docs.x.ai/developers/tools/x-search)
