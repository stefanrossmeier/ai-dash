# Independent runtime

AI Dash retains its own Windmill/database/application state and LLM gateway
configuration, secrets and accounting. It does not depend on DailyDash.

Inference uses the dedicated authenticated LLM gateway. Normal X retrieval uses
free Nitter RSS; ranking/consolidation still use paid chat inference. The copied
ranking gateway and dormant paid-X service have been retired. The paid-X removal
is a separate Git commit so its prior implementation remains discoverable.
Private historical X budgets/audits are retained, not reset or republished.

The worker uses `AI_DASH_GATEWAY_URL` and `AI_DASH_GATEWAY_TOKEN_FILE`. Standalone
CLI commands default to port 18182; override the URL as appropriate. There is no
legacy provider fallback. Provider keys belong only at the gateway boundary.

Scheduled jobs derive stable identity from `WM_ROOT_FLOW_JOB_ID`/`WM_JOB_ID`.
For manual runs set `AI_DASH_RUN_ID` to a new logical run ID and reuse it after
interruption. A transport failure queries the original request; it never starts
a fresh paid attempt automatically. Result recovery requires gateway result
retention. Inspect gateway `/v1/usage` with the project token for cost/exposure.

Deploy the application with `scripts/deploy-vps.sh`, preserving runtime secrets,
application state, schedule enablement and the database. Provision its gateway
independently from the reviewed release and attach the application worker to the
owned internal gateway network. Use authenticated readiness checks before enabling
jobs. Never run `down -v` or delete accounting state to regain allowance.

Every report derives its retrieval window from its own daily slots. Daily reports
use the preceding scheduled interval plus one hour (normally 25 hours); more
frequent reports use the preceding interval plus two hours. Uneven schedules and
daylight-saving changes use the actual preceding interval. X and YouTube use the
same policy. There is no multi-day catch-up window.

Unsent editions are retained for audit as `discarded` or `discarded_uncertain`.
They are never replayed on a subsequent run. Each run discards any interrupted
send before checking Telegram and retrieving fresh data. Successful messages
remain in delivery history. A failed send still marks the run failed for monitoring.

The active gateway input allowance is 262144. The client uses
`AI_DASH_GATEWAY_INPUT_LIMIT` (default 262144) with framing headroom to split
oversized ranking and summary batches. Explicit gateway input-limit rejections
also split recursively without dropping candidates. Unknown outcomes and unrelated
errors are never retried through this path. Keep this setting aligned with the
project-owned gateway policy; spending caps and provider credentials remain there.

r/singularity uses the approved Reddit OAuth Data API because its public RSS can
reject this host. Provision `reddit_client_id`, `reddit_client_secret`, and
`reddit_user_agent` as one-value files in this project's private runtime secret
directory (directory mode 0700, files mode 0600). Use a descriptive ai-dash
User-Agent with the Reddit account owner's contact. The worker mounts only these
files read-only; values are never copied into source, images, artifacts or logs.
`AI_DASH_REDDIT_CLIENT_ID_FILE`, `AI_DASH_REDDIT_CLIENT_SECRET_FILE`, and
`AI_DASH_REDDIT_USER_AGENT_FILE` can override the default mounted paths for an
operator's standalone CLI. OAuth access tokens remain in memory. No other
project's runtime or Windmill credentials are accessed by the application.
