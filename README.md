# ai-dash

Source-based AI engineering reports in English, delivered to an independent Telegram
bot and channel. Owns its Windmill instance, database, workers, model gateways,
configuration, secrets and delivery history. Deploys independently on the deployment-host VPS.

| Report | Sources | Berlin slots |
| --- | --- | --- |
| Company & Product Updates | 20 official lab/company/product streams | 07:30, 17:30 |
| Blogs & Analysis | 7 independent author, newsletter and reporting streams | 12:30 |
| Research & Open Source | 24 paper, model, release and community sources | 15:30 |
| X — AI Leaders & Evaluations | 3 complementary accounts | 20:30 |

Configuration is in [config/reports.yaml](config/reports.yaml). These source groups
are disjoint; one report never triggers the other reports' collectors.
The old mixed digest and its four schedules are retired.

## X verification status

The corrected request was verified on 2026-11-09 with one user-authorized paid call:
**one scoped search, two cited fresh posts, reported cost $0.060482**. Long-form X
posts initially exceeded a local text cap; the parser was corrected and the saved
response was replayed successfully without another provider request.

The X report is enabled at 20:30 Berlin. The earlier failed $1.03470405 test and
its corrective work are recorded in [the X fix audit](docs/X_REPORT_FIX.md).

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
tool calls or exact dollar cost. Ranking/summarization still uses the AI Dash-owned cheap
gateway alias. Each artifact records reported usage and cost; cached retrieval
records zero new usage. No automatic fallback widens the watchlist.

## Delivery and editorial policy

Source dates required; bounded catch-up windows of 48 hours for company news,
72 hours for research/OSS and seven days for analysis. X keeps its rolling 24-hour
window. Messages show the actual publication, submission, curation or repository
update date; update/curation timestamps never establish a new release.
Canonical URL and scoped-title dedupe, semantic event consolidation, English
summaries, source attribution and direct links.
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

[Deployment](docs/DEPLOYMENT.md) · [Independence audit](docs/INDEPENDENCE.md) · [Telegram setup](docs/TELEGRAM.md) ·
[Source provenance](docs/SOURCES.md) · [Deployment evidence](docs/DEPLOYMENT_STATUS.md).

```bash
# On deployment-host, deploy the standalone stack; new schedules start disabled.
# Existing schedule enablement is preserved on updates.
./scripts/deploy-vps.sh
# Enable each report only after its example has succeeded.
python3 scripts/register-windmill.py --enable-report company
# Or enable all four after their separate rollouts.
python3 scripts/register-windmill.py --enable
# Pause one report without changing the others.
python3 scripts/register-windmill.py --disable-report blogs
```

Flows live exclusively under `f/ai_dash`, with worker tag `aidash`. Start one flow
with input `{"example": true}` to deliver its example immediately. Never reset
history to force a sample. Source and model failures remain visible in private
artifacts and per-report collection checkpoints.

Feed bodies are preferred over teasers. A bounded public-article/model-card reader
hydrates thin candidates (up to 40 article requests per report, ten-second request
timeout, two-MB response cap); inaccessible text is never invented. AINews can
supply up to eight linked discoveries per issue, accepted only after verifying
their publisher dates. The duplicate Latent Space feed alias is archived.
GPT-6 Luna at low reasoning effort evaluates every evidenced candidate in batches
of up to 150 using source-neutral headlines and 1,200-character facts excerpts.
Publication requires a joint impact/breadth score of 65 (60 for research), impact 60, breadth 45,
novelty 40, evidence quality 60 and tier 3; routine updates never qualify.
A global comparison consolidates qualifying events before paper/story limits and
publisher diversity; only final selections receive full-evidence summaries.
Rejected items incur no summary-generation call. Missing model decisions fail visibly instead of
silently producing an empty edition. `ai-dash status` exposes latest report health;
artifacts/checkpoints contain evidence gaps and per-candidate selection logs.

The [news audit](docs/NEWS_AUDIT_2026-11-15.md) records the production baseline;
[repair verification](docs/NEWS_REPAIR_2026-11-15.md) describes the changes and limits.
The [impact ranking policy](docs/IMPACT_RANKING.md) documents the high-signal thresholds
and the lightweight DailyDash-inspired ranking design.

Private data: `/var/code/ai-dash-data`. New bot credentials:
`/var/code/ai-dash-runtime/secrets`. Back up data and encrypted secrets independently.
To resolve an uncertain send after inspecting the channel:

```bash
uv run ai-dash status --data-dir /private/path/ai-dash-data
uv run ai-dash resolve-delivery --run-id RUN_ID --part 0 --resolution sent
```

## License

Apache-2.0. Source provenance and endpoint adaptations are documented explicitly.
