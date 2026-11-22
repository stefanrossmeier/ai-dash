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
