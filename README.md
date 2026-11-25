# AI Dash

Self-hosted AI news briefings delivered to Telegram. AI Dash collects public feeds,
articles, model hubs, releases, community posts and video uploads; ranks relevant
developments; and keeps inspectable evidence of selection and delivery.

This is a single-operator reference application. The repository is currently private.

## Reports

| Report | Inputs | Europe/Berlin slots |
| --- | --- | --- |
| Company & Product Updates | Company blogs and product announcements | 07:30, 17:30 |
| Blogs & Analysis | Independent commentary and newsletters | 12:30 |
| Research & Open Source | Papers, model hubs, releases and engineering discoveries | 15:30 |
| X — AI Voices | Fourteen configured public accounts through Nitter RSS | 07:45, 11:45, 19:45 |
| Reddit — r/singularity Daily | Approved Reddit OAuth listing | 08:30, 18:30 |
| AI News — Tech Press Digest | Four configured tech-press feeds | 09:15, 19:15 |
| YouTube — New Videos | Upload feeds for configured channels; no LLM processing | 19:30 |

The 119-row source registry includes archived and manual entries; it is not a claim
that every source is collected or available. The configuration is authoritative:
[reports](config/reports.yaml), [sources](config/sources.yaml) and
[YouTube channels](config/youtube_channels.yaml).

## What makes it useful

Article hydration supplies evidence beyond headlines. Timestamp labels distinguish
publication, community submission, curation and repository activity. Deterministic
impact gates, event consolidation, paper caps and delivery history help control
noise. Coverage and rejection diagnostics remain visible in private artifacts.

Retrieval windows follow the preceding scheduled interval plus a small overlap,
including uneven slots and daylight-saving changes. Failed unsent editions are
retained for audit and discarded; the next run retrieves fresh data.

AI Dash is a domain application alongside
[DailyDash](https://github.com/stefanrossmeier/daily-dash), which covers markets.
It uses an independently deployed
[LLM Gateway](https://github.com/stefanrossmeier/llm-gateway), with its own policy,
tokens and accounting. It does not require another application's runtime.

## Local checks

Requires Python 3.12+ on macOS or Linux, and `uv`. From this checkout:

```sh
uv sync --frozen --no-editable
uv run --no-sync ai-dash validate
./scripts/check.sh
```

These checks need no provider keys, Telegram account or running Windmill instance.
CI also scans the checkout and Git history for secrets with a pinned Gitleaks binary.

## Running a briefing

Deployment needs Docker Compose, an owned Windmill/database stack, a separate
authenticated gateway for model-backed reports, a Telegram bot/channel and approved
Reddit OAuth credentials for the configured Reddit report. Start with
[deployment](docs/DEPLOYMENT.md), [Telegram](docs/TELEGRAM.md) and
[operations](docs/archdoc/OPERATIONS.md).

For manual inference, set `AI_DASH_GATEWAY_TOKEN_FILE` and an explicit
`AI_DASH_RUN_ID`; reuse that ID when recovering an interrupted request. `preview`
does not deliver messages, but model-backed previews can incur inference cost.
`collect` uses source networking without model inference; `run` can incur model
cost and posts to the configured Telegram channel.

Normal X collection uses free, volunteer-operated Nitter RSS, whose availability
and timeline completeness are not guaranteed. Ranking, consolidation and summaries
still use paid inference. The YouTube report lists uploads without watching videos,
retrieving transcripts or claiming to summarize their contents.

## Documentation

- [Documentation index](docs/README.md)
- [Repository map](docs/archdoc/REPO_MAP.md), [architecture](docs/archdoc/ARCHITECTURE.md),
  [interfaces](docs/archdoc/API_SURFACE.md), [operations](docs/archdoc/OPERATIONS.md)
- [Source provenance](docs/SOURCES.md) and [impact policy](docs/IMPACT_RANKING.md)
- [Privacy, security and publication review](docs/REVIEW_2026-11-25.md)

Private ledgers, channel identifiers, delivery history, raw operational evidence
and credentials belong outside published source. Never delete accounting state to
regain allowance. Licensed under [Apache 2.0](LICENSE).
