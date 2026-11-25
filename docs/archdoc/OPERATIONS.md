# AI Dash operations

Reviewed 25 November 2026. Use [deployment](../DEPLOYMENT.md) for prerequisites,
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
reports latest persisted report health and outbox counts. Private collection
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
