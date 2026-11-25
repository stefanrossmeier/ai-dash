# Independent runtime

AI Dash retains its own Windmill/database/application state and LLM gateway
configuration, secrets and accounting. It does not depend on DailyDash.

## Prerequisites and configuration

Use a Linux host with Docker Compose and Python 3 with PyYAML available to the
host-side registration scripts. The application image installs its own frozen
Python dependencies. This is a repository deployment, not a standalone wheel
installation: source registries, prompt assets and workflow definitions are
required alongside the package.

Provision the project's own gateway using the
[LLM Gateway deployment documentation](https://github.com/stefanrossmeier/llm-gateway/blob/main/docs/OPERATIONS.md).
It must expose the authenticated dashboard-compatible chat/recovery interfaces,
the `rank-cheap` alias and readiness for the `ai-dash` principal. Its internal DNS
name in the application network is `ai-dash-llm-gateway`. Provider keys and durable
accounting remain in that gateway's deployment.

Before running `scripts/deploy-vps.sh`, provision the independent Telegram secrets
and all three Reddit OAuth files described below. The current Compose template
binds the Reddit files unconditionally; missing files stop deployment even if the
Reddit report is disabled. File mounts fail rather than creating empty directories.

Set `AI_DASH_GATEWAY_NETWORK` to the gateway's owned internal client network and
`AI_DASH_GATEWAY_TOKEN_SOURCE` to its private bearer-token file. The network must
already exist. Default runtime/data paths are templates for a dedicated host;
override `AI_DASH_RUNTIME`, `AI_DASH_DATA_SOURCE`, `AI_DASH_SECRETS_SOURCE` and
`AI_DASH_SOURCE` when using different private locations. Do not commit the runtime
`.env` or operator profile. See [Telegram](TELEGRAM.md) for bot/channel provisioning.

## Inference and deployment

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

The default client input allowance is 262144. The client uses
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

## Public-source fetching

Feed, HTML, article, YouTube and Nitter connections reject private or mixed
public/private DNS results, pin the connection to a checked IP and retain the
original HTTP Host and TLS certificate identity. Redirect targets pass the same
checks. Public-source clients ignore environment proxies, request identity
encoding and reject compressed responses before decoding. Source responses are
streamed with a 12 MB limit; article evidence has a 2 MB limit. A publisher that
does not honor identity encoding is recorded unavailable rather than decoded
without a bound. Credential-bearing Reddit, gateway and Telegram clients remain
separate from this transport.

Run `scripts/smoke-test.sh` after deployment. It reads the gateway token inside
the worker; the operator does not need direct host access to the protected file.
The check verifies readiness and infrastructure, not paid inference quality or
Telegram notification delivery. Registration preserves existing schedule states;
new schedules default to disabled until explicitly enabled with bot preflight.
