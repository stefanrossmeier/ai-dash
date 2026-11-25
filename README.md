# AI Dash

AI news digests with independent configuration, prompts, state, Windmill runtime
and Telegram delivery. This repository remains private.

X timeline collection uses free Nitter RSS only. Paid X retrieval and copied
provider gateways were removed. Ranking, summarization and consolidation still
use the authenticated project LLM gateway and can incur model cost.

Reports, source lists, thresholds and schedule slots are defined in
`config/reports.yaml` and `config/sources.yaml`. Retrieval windows follow each report's
cadence with a small overlap. Failed unsent editions are discarded; the next run
retrieves fresh data. Each logical inference uses durable job/run identity.

```sh
uv sync --frozen
uv run ai-dash validate
./scripts/check.sh
```

See [deployment](docs/DEPLOYMENT.md), [independence](docs/INDEPENDENCE.md),
[sources](docs/SOURCES.md) and [Telegram](docs/TELEGRAM.md). Manual inference needs
`AI_DASH_GATEWAY_TOKEN_FILE` and an explicit `AI_DASH_RUN_ID`; reuse that ID after
interruption. Gateway `/v1/usage` is the cost/exposure inspection API. Do not reset
private ledgers, delivery history or preserved historical X audit data.
