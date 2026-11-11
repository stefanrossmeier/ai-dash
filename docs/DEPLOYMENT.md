# Independent deployment on deployment-host

AI Dash owns its entire Compose project (`ai-dash`), Windmill server and workers,
PostgreSQL database, Docker network/volumes, model gateway and X gateway. All
runtime code and model settings come from this repository. No external Docker
network, database, CLI profile, source checkout or daily-dash service is required.

- Source checkout: `/var/code/ai-dash`
- Persistent application data, history, outbox and X budgets: `/var/code/ai-dash-data`
- Private runtime configuration: `/var/code/ai-dash-runtime/.env`
- Private operator profile: `/var/code/ai-dash-runtime/windmill-profile.json`
- Credentials: `/var/code/ai-dash-runtime/secrets`
- Windmill workspace: `ai-dash`; definitions: `f/ai_dash`; application tag: `aidash`

## Install

Clone this repository, install Docker Compose and host Python 3 with PyYAML, and
place `openrouter_api_key`, `telegram_token` and `telegram_chat_id` in the private
secrets directory (mode 600, directory mode 700). Use the AI Dash bot/channel.

```bash
cd /var/code/ai-dash
./scripts/deploy-vps.sh
```

The deploy script generates a new database password once, builds the locked
application image, starts only the `ai-dash` project, waits for health checks,
bootstraps its Windmill workspace and registers definitions with schedules disabled.
It replaces Windmill's default administrator password on first startup. The private
password is in `secrets/windmill_admin_password`; login email is `admin@windmill.dev`.
All administration and registration use only this runtime's profile.
`AI_DASH_RUNTIME`, `AI_DASH_DATA_SOURCE` and `AI_DASH_SECRETS_SOURCE` can override
host paths. Set port overrides in the generated runtime `.env`.

Loopback endpoints on deployment-host:

| Service | Endpoint |
| --- | --- |
| Windmill UI/API | `http://127.0.0.1:18090` |
| Ranking gateway | `http://127.0.0.1:18082` |
| Bounded X gateway | `http://127.0.0.1:18081` |

Access Windmill from your workstation with `ssh -L 18090:127.0.0.1:18090 deployment-host`
and open `http://127.0.0.1:18090`. No proxy from another project is involved.
Inside Docker, jobs use `ai_dash_model_gateway:8080` and `ai_dash_x_gateway:8080`.
The ranking configuration is `config/model-gateway.yaml`, built into AI Dash's image.
The gateway implementation was copied under Apache-2.0 and is maintained here.
The bounded X implementation and all existing reservation/cache limits are preserved.

Only gateways mount the AI Dash-owned OpenRouter credential file. The application
worker mounts only its two Telegram credential files, not provider/admin credentials.
The default worker handles flow orchestration; the application worker handles `aidash` jobs.

## Verify and enable

```bash
docker exec ai-dash-windmill_worker_aidash-1 /opt/ai-dash/.venv/bin/ai-dash check-telegram
docker exec ai-dash-windmill_worker_aidash-1 /opt/ai-dash/.venv/bin/ai-dash collect \
  --report company --output /data/ai-dash/collection-smoke.json
curl --fail http://127.0.0.1:18082/health
curl --fail http://127.0.0.1:18081/health
python3 scripts/register-windmill.py --enable
```

Health checks, collection and Telegram preflight do not send messages or make paid
model/search calls. `preview` uses paid ranking; X collect/preview can consume the
persistent daily X attempt. Reuse existing caches and never reset reservations.

Reports retain their Europe/Berlin slots: company 07:30/17:30, blogs 12:30,
research/open source 15:30, X 20:30. Registration honors explicit report pauses.
An application lock protects overlap; delivery history/outbox prevents duplicates.

## Update, stop and rollback

Pull a tested revision and run `deploy-vps.sh`. Verify and explicitly re-enable
schedules. Revert code and redeploy to roll back; preserve data and runtime secrets.
Operate only the owned project:

```bash
docker compose -p ai-dash --env-file /var/code/ai-dash-runtime/.env \
  -f deploy/compose.ai-dash.yaml ps
docker compose -p ai-dash --env-file /var/code/ai-dash-runtime/.env \
  -f deploy/compose.ai-dash.yaml stop
```

Back up the application data, runtime secrets/profile and the `ai-dash_db_data`
PostgreSQL volume. Never use `down -v` during an application update.

## Migration from the former shared runtime

This is a one-time operational cutover, not a deployment dependency:

1. Disable only the old `f/ai_dash/*` schedules and confirm no AI Dash job is running.
   Disabling removes their future queued executions. Keep other projects running.
2. Back up AI Dash's data and copy the reused provider credential once into its
   own secrets directory. That file can subsequently be rotated independently.
3. Deploy this stack with schedules disabled. Keep the existing application data,
   Telegram bot/channel, outbox, X reservations and provider cache.
4. Verify health, registration, flow execution and Telegram permissions. Enable the
   five schedules in the new `ai-dash` workspace only after old schedules are disabled.
5. Remove the two retired AI Dash containers from the former Compose project.
   Keep the old disabled definitions/job history as migration evidence.

The copied OpenRouter key initially uses the same provider account/key value; there
is no shared filesystem or service dependency. A separately issued key can replace
this file without changing daily-dash. See [the independence audit](INDEPENDENCE.md).
