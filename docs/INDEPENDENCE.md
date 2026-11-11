# Dependency audit and separation — 2026-11-11

| Former coupling | Independent replacement |
| --- | --- |
| Deployment used the other project's Compose files, `.env` and project name | Standalone checked-in Compose project `ai-dash` and generated private runtime `.env` |
| Shared Windmill server, Postgres DB, queue and orchestration workers | AI Dash-owned Windmill instance, database, workers, network and named volumes |
| Ranking depended on `daily_dash_model_gateway` and its mutable alias configuration | Copied structured ranking implementation in `ai_dash.model_gateway`, own `config/model-gateway.yaml` and service |
| X gateway mounted the other runtime's provider credential | AI Dash-owned credential file mounted by both owned gateways |
| Registration read the `daily-dash-local` global CLI profile | Dedicated private runtime profile and `ai-dash` workspace bootstrap |
| Telegram preflight read the other bot's secret | Preflight uses only AI Dash's existing independent bot/channel |
| Job wrapper default routed ranking back to the other project | Default routes only to `ai_dash_model_gateway` |
| CLI default port targeted the other project's gateway | Own ranking port 18082, X port 18081 and Windmill port 18090 |
| Documentation instructed deploying and stopping inside the shared project | Standalone installation, upgrade, backup, stop and rollback instructions |

The original ranking behavior is preserved: `rank-cheap` initially selects
`openai/gpt-6-luna`, with three bounded attempts of the same model and structured
response validation. Changes to daily-dash's model aliases no longer affect AI Dash.
The unnecessary legacy X endpoint was excluded from the copied ranking gateway;
paid X retrieval remains exclusively in the existing bounded AI Dash service.

The source registry, editorial configuration, Telegram bot/channel, application
SQLite state, artifacts, delivery history and X budgets already belonged to AI Dash
and remain in place. Reusing that data during cutover preserves deduplication and
cost guards. Neither project imports the other's package or checks out its code.

The VPS host, Docker daemon, upstream Windmill/Postgres images, Telegram and
OpenRouter remain infrastructure/provider dependencies. The provider key is copied
once into an independent file; its initial account/key value remains the same.
Issuing a new upstream key would also isolate provider revocation/billing policy.
No ongoing read, network or deployment dependency on daily-dash remains.

Regression coverage checks standalone Compose ownership, production defaults,
private runtime initialization, model alias/schema validation, retry deadlines and
provider metadata. Existing delivery and bounded X regressions remain unchanged.
