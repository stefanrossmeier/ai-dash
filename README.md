# ai-dash

Source-based AI engineering reports in English, delivered to an independent Telegram
bot and channel. Shares the existing VPS, Windmill installation and model gateway;
application code, worker, secrets, data and delivery history are separate from daily-dash.

| Report | Sources | Berlin slots |
| --- | --- | --- |
| Company & Product Updates | 18 official lab/company/product blogs | 07:30, 17:30 |
| Blogs & Analysis | 6 independent authors, newsletters and aggregators | 12:30 |
| Research & Open Source | 22 paper, model, release and community sources | 15:30 |
| X — AI Leaders & Evaluations | 3 complementary accounts | Paused |

Configuration is in [config/reports.yaml](config/reports.yaml). These source groups
are disjoint; one report never triggers the other reports' collectors.
The old mixed digest and its four schedules are retired.

## X verification status

The user-authorized paid test on 2026-11-09 failed acceptance: one uncached request
cost $1.03470405, its provider trace reported 18 search queries including accounts
outside the requested three, and it returned zero structured posts. X is disabled
in `config/reports.yaml`; workspace registration respects that flag even with
`--enable`. The other reports continue running. No further paid test was made.
The configured 20:30 slot is retained for after the provider integration is repaired
and verified. One application request does not imply one provider-side search.

## Cost control

The original 95-row Hermes source registry is retained for provenance. Its 45 X
entries are disabled by default. Only the daily X report explicitly selects
Andrej Karpathy, François Chollet and Artificial Analysis. Official lab accounts
are excluded because their blogs/model hubs are already collected.

- One batched X retrieval attempt per Europe/Berlin calendar day, at most seven accounts.
- At most two posts per account and six selected stories.
- A durable SQLite reservation is committed BEFORE the provider request.
- Failures, timeouts and crashes consume the daily attempt; there is no paid retry.
- Successful results are cached; previews and manual reruns reuse them at zero retrieval cost.
- At most one X edition is delivered each day, including quiet-day editions.
- Other reports have no X sources and cannot invoke paid X retrieval.

This limits application retrieval requests, not the native search engine's internal
tool calls or exact dollar cost. Ranking/summarization still uses the cheap shared
gateway alias. Each artifact records reported usage and cost; cached retrieval
records zero new usage. No automatic fallback widens the watchlist.

## Delivery and editorial policy

24-hour publication window, source dates required, canonical URL/title dedupe,
semantic selection, English summaries, source attribution and direct links.
Research & Open Source permits at most six papers; papers never fill company/blog/X reports.
Global history prevents the same announcement appearing repeatedly across reports.
Empty normal editions are quiet, except the daily X report. `--example` labels a
sample and can explain a quiet source group without repeating delivered stories.

Every run persists an immutable artifact before Telegram delivery. The durable
outbox records individual message acknowledgements and resumes pending sends.
Uncertain sends stop for operator resolution. One persistent process lock protects
all reports; a separate persistent X budget also protects collect/preview commands.

## Development

Python 3.12 and uv:

```bash
uv sync --frozen
./scripts/check.sh
uv run ai-dash validate
uv run ai-dash collect --report company --output /tmp/company.json
uv run ai-dash preview --report blogs --output /tmp/blogs.json
```

`--report` is mandatory for collection, preview and delivery. Gateway settings and
private secret-file paths are in `.env.example`; real secrets belong outside the
public checkout. X previews count against the same daily retrieval budget.

## Deploy and operate

[Deployment](docs/DEPLOYMENT.md) · [Telegram setup](docs/TELEGRAM.md) ·
[Source provenance](docs/SOURCES.md) · [Deployment evidence](docs/DEPLOYMENT_STATUS.md).

```bash
# On deployment-host, rebuild only ai-dash's worker; schedules register disabled.
./scripts/deploy-vps.sh
# Enable each report only after its example has succeeded.
python3 scripts/register-windmill.py --enable-report company
# Or enable all four after their separate rollouts.
python3 scripts/register-windmill.py --enable
```

Flows live exclusively under `f/ai_dash`, with worker tag `aidash`. Start one flow
with input `{"example": true}` to deliver its example immediately. Never reset
history to force a sample. Source and model failures remain visible in private
artifacts and per-report collection checkpoints.

Private data: `/var/code/ai-dash-data`. New bot credentials:
`/var/code/ai-dash-runtime/secrets`. Back up data and encrypted secrets independently.
To resolve an uncertain send after inspecting the channel:

```bash
uv run ai-dash status --data-dir /private/path/ai-dash-data
uv run ai-dash resolve-delivery --run-id RUN_ID --part 0 --resolution sent
```

## License

Apache-2.0. Source provenance and endpoint adaptations are documented explicitly.
