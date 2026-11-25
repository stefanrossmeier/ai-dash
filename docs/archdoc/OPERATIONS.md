# AI Dash operations

- Review Scope: delta — published history, provenance and evidence-link refresh
- Doc Status: MAINTAINED
- Last Updated: 2026-11-25T17:49:49Z
- Updated By: agent using [ai-craftkit archdoc](https://github.com/stefanrossmeier/ai-craftkit/blob/ad6f29457e2a1fa43300f34a8f44691251f9c2a2/skills/archdoc/SKILL.md)
- Source Repository: [ai-dash tree](https://github.com/stefanrossmeier/ai-dash/tree/f5fd37128a569a908f31f21e2ae07047ea25b4cf)
- Source Revision: [f5fd37128a569a908f31f21e2ae07047ea25b4cf](https://github.com/stefanrossmeier/ai-dash/commit/f5fd37128a569a908f31f21e2ae07047ea25b4cf)
- Source Basis: runtime/Compose configuration, deploy/register/smoke scripts, CLI, persistence, cadence and failure regressions.

Unless marked otherwise, implementation descriptions below are **verified** against
this revision. Source Revision identifies the inspected source snapshot, before
this documentation update. This is repository evidence, not a claim about live deployment.

Use [deployment](../DEPLOYMENT.md) for prerequisites,
network/secret inputs and gateway provisioning. No other application's checkout,
runtime, credentials or operator profile is required.

## Setup and routine checks

```sh
uv sync --frozen --no-editable
./scripts/check.sh
```

The offline gate checks source, tests, configuration, generated workflows and
package builds. CI additionally scans full available Git history and the checkout
for credentials. A successful scan is scoped evidence, not a guarantee that an
account or runtime has never been compromised.

The Compose application comprises PostgreSQL, a loopback-bound Windmill server,
an orchestration worker and an application worker. The authenticated gateway is
deployed independently and joined through the explicitly owned internal network.
The current worker image runs as root; use only trusted operator-managed jobs.
The default Compose mounts require the independent Telegram and Reddit files.

`scripts/init-runtime.py` creates private runtime configuration only when absent.
Existing secrets and state are preserved. `scripts/deploy-vps.sh` builds the worker,
starts/waits for the stack, bootstraps Windmill and registers workflow definitions.
It preserves existing schedule enablement; new schedules remain disabled.

After bot/channel and authenticated gateway checks, enable the intended schedules
with `scripts/register-windmill.py --enable` or `--enable-report ID`. Selective
pauses use `--disable-report ID`. Registration uses only the owned runtime profile.
Schedule edits belong in report config followed by workflow regeneration.

## Configuration and execution modes

| Input | Source and purpose |
| --- | --- |
| `AI_DASH_HOME`, `AI_DASH_DATA_DIR` | Checkout assets and private state roots; CLI defaults to `.` and `./var` |
| `AI_DASH_GATEWAY_URL`, `AI_DASH_GATEWAY_TOKEN_FILE`, `AI_DASH_RUN_ID` | Owned gateway, bearer file and stable manual inference identity |
| `AI_DASH_TELEGRAM_TOKEN_FILE`, `AI_DASH_TELEGRAM_CHAT_ID_FILE` | Independent bot and destination; required for run/check |
| `AI_DASH_REDDIT_CLIENT_ID_FILE`, `AI_DASH_REDDIT_CLIENT_SECRET_FILE`, `AI_DASH_REDDIT_USER_AGENT_FILE` | Private credentials/contact configuration for Reddit collection |
| `AI_DASH_RUNTIME`, `AI_DASH_SOURCE`, `AI_DASH_DATA_SOURCE`, `AI_DASH_SECRETS_SOURCE` | Deployment script inputs; separate checkout/runtime/data/secret paths |
| `AI_DASH_GATEWAY_NETWORK`, `AI_DASH_GATEWAY_TOKEN_SOURCE`, `WM_IMAGE` | Compose gateway boundary, private token mount and upstream base |

`validate` and the offline gate need no service; `collect` needs source networking;
model-backed `preview` needs authenticated inference; `run` additionally needs
private state and Telegram. Windmill supplies run identity for scheduled jobs.
Names/defaults are verified in [src/ai_dash/cli.py](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/src/ai_dash/cli.py),
[src/ai_dash/gateway.py](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/src/ai_dash/gateway.py), [scripts/deploy-vps.sh](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/scripts/deploy-vps.sh)
and [deploy/compose.ai-dash.yaml](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/deploy/compose.ai-dash.yaml). See [interfaces](API_SURFACE.md)
for credential validation and side effects. Do not paste values into diagnostics.

## Retrieval windows

The configured timezone is Europe/Berlin. Each report uses the interval between
its last two scheduled slots, plus one hour for a once-daily report or two hours
for more frequent reports. UTC elapsed time accounts for daylight-saving changes.
Delayed manual runs use the most recent scheduled interval, not a multi-day backlog.

| Report | Normal window by slot |
| --- | --- |
| Company | 16 hours at 07:30; 12 hours at 17:30 |
| Blogs / research / YouTube | 25 hours; 24 or 26 across a one-hour DST transition |
| X | 14 hours at 07:45; 6 at 11:45; 10 at 19:45 |
| Reddit | 16 hours at 08:30; 12 at 18:30 |
| Tech press | 16 hours at 09:15; 12 at 19:15 |

X and YouTube intentionally repeat eligible items across overlapping editions.
Other reports use delivery history. Feed length and publisher availability can
still cause missed items; windows do not create a durable discovery queue.

## Health and diagnostics

Run `scripts/smoke-test.sh` on the host. It checks the source revision, workers,
database, Windmill, authenticated gateway readiness, schedules, state readability
and recorded infrastructure errors. The gateway token is read in the worker,
where its permissions apply. This makes no paid inference or Telegram send.

`ai-dash check-telegram` checks permissions without posting. `ai-dash status`
reports latest persisted selection and delivery outcomes, part acknowledgements,
report warnings and outbox counts. The smoke check prints per-report outcomes as
`INFO`, separately from infrastructure pass/fail. `no_qualifying_stories` warrants
inspection when unexpected; `acknowledged` is an API receipt, not a client notification. Private collection
checkpoints retain failure evidence even before an artifact is persisted. Inspect
Windmill failures as well: a failed run may have no new persisted edition.

The smoke checker currently assumes every registered application schedule should
be enabled; intentionally paused schedules require interpretation. Readiness is
not evidence of current model answer quality, source completeness or Telegram
client notifications. No dedicated operator alert destination is built in.

## Recovery and backups

Back up the source revision, private application state/artifacts, owned Windmill
PostgreSQL database, runtime configuration/profile and gateway state through its
own supported backup procedure. Use SQLite's backup API or stop writers; copying
only `state.sqlite` while WAL writes continue is not a consistent backup. Restrict
backup access because SQLite contains channel destinations and message bodies.

Fresh runs discard older unsent messages, retaining `discarded` or
`discarded_uncertain` audit status. They do not replay buffered news. Successful
acknowledgements remain. Inspect the Telegram channel when an acknowledgement is
uncertain; do not relabel it sent without evidence. Partial editions reserve all
their stories in history once one part is sent; per-story delivery tracking is
not implemented.

Reuse the logical inference run/request ID after interruption. Recover retained
results and inspect gateway usage/exposure before considering another request.
Explicit pre-dispatch input limits can split ranking/summary batches; unrelated
errors and unknown outcomes do not take that path. Never clear private ledgers,
delivery history or old X accounting to regain allowance.

For upgrades, verify a clean checkout, record the prior commit, back up state,
deploy a reviewed commit and compare installed source, schedule states, readiness
and history continuity. A fleet backup/restore drill and service-level objectives
remain operator work; this repository does not automate them end to end.

Use the current public repository directly for development and deployment.
Do not merge or push history from the frozen private archive into it; see the
[history sanitization record](../HISTORY_SANITIZATION.md).

## Evidence, release checks and unresolved work

Build evidence: [scripts/check.sh](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/scripts/check.sh), [scripts/check-distributions.py](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/scripts/check-distributions.py)
and [deploy/windmill-worker.Dockerfile](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/deploy/windmill-worker.Dockerfile). The Docker build copies
both license files required by package metadata before installing the application.
A wheel alone omits policy/assets/workflows needed for full deployment.

Runtime evidence: [scripts/init-runtime.py](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/scripts/init-runtime.py), [scripts/deploy-vps.sh](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/scripts/deploy-vps.sh), [scripts/register-windmill.py](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/scripts/register-windmill.py) and [scripts/smoke-test.sh](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/scripts/smoke-test.sh).
Selection checkpoints and artifacts are written by [src/ai_dash/pipeline.py](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/src/ai_dash/pipeline.py);
delivery/history states are owned by [src/ai_dash/storage.py](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/src/ai_dash/storage.py).
Cadence/DST behavior is covered in [tests/test_cadence.py](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/tests/test_cadence.py).

A total source outage fails before ranking; inspect coverage/checkpoints and repair
access rather than weaken dates or generate invented news. A gateway outage or
unknown response requires request recovery with the same identity; readiness alone
does not prove remaining allowance or model quality. A Telegram failure can be
uncertain even when the next infrastructure check passes; inspect channel and
edition/outbox evidence before interpreting recovery.

**Missing:** automated complete restore verification, service-level objectives and
a separate built-in operator alert destination. **Unresolved:** the default root
worker, inherited image advisories and permitted upstream image modification/
distribution route. The [publication review](../PUBLICATION.md) scopes that evidence;
a successful deployment does not establish image-release approval. This document
records repository procedures, not the result of a particular live deployment.
