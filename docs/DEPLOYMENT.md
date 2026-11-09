# Deploy beside the existing Windmill installation

Source: `/var/code/ai-dash`. Private artifacts/SQLite: `/var/code/ai-dash-data`.
Secrets: `/var/code/ai-dash-runtime/secrets`. Use a NEW Telegram bot and channel.
The existing shared Windmill runtime is `/var/code/daily-dash-windmill-local`.

## Install

Copy the tested checkout to `/var/code/ai-dash` (or clone once the code is pushed).
On the VPS:

```bash
cd /var/code/ai-dash
./scripts/deploy-vps.sh
```

The script adds only `windmill_worker_aidash` to the current Compose project, using
`--no-deps` to avoid restarting the database, existing workers or model gateway.
It shares the existing DB/network and tags its jobs `aidash`. The image installs
only ai-dash and its locked Python dependencies. No ports are published.

The current shared model gateway is available on its internal Docker DNS name
`daily_dash_model_gateway:8080`. Override `AI_DASH_GATEWAY_URL` in the worker
configuration to move to a separate compatible gateway later. This is the only
shared application service; ai-dash does not read daily-dash news, bot credentials,
configuration or delivery state. The registration preflight only compares the bot
tokens privately to guard against accidentally reusing the daily-dash bot.

`register-windmill.py` reads the existing operator Windmill CLI profile privately
and upserts ONLY the folder, script, flow and schedules under `f/ai_dash`.
It does not perform a workspace-wide synchronization, deletion or secret copy.
Schedules register disabled by default, including on redeployment.
The host needs Python 3 and PyYAML (present on this VPS).

## Configure and check the independent bot

Follow [TELEGRAM.md](TELEGRAM.md). Then:

```bash
WORKER=$(docker ps -q --filter name=windmill_worker_aidash)
docker exec "$WORKER" /opt/ai-dash/.venv/bin/ai-dash check-telegram
# Collection smoke test: no Telegram send, no X provider cost.
docker exec "$WORKER" /opt/ai-dash/.venv/bin/ai-dash collect --report company \
  --output /data/ai-dash/collection-smoke.json
# Model-backed preview, still no delivery/history update.
docker exec "$WORKER" /opt/ai-dash/.venv/bin/ai-dash preview --report company \
  --output /data/ai-dash/preview-smoke.json
```

Only enable once Telegram and collection/model checks pass:

```bash
python3 scripts/register-windmill.py --enable
```

This checks the NEW bot's channel and posting permission before activation.
Report slots are defined in `config/reports.yaml`: company 07:30/17:30, blogs 12:30,
research/open source 15:30, X 20:30, all Europe/Berlin;
Windmill handles daylight saving time. The application lock protects overlap
across manual runs and different schedule entries too.

Run one of `f/ai_dash/company`, `blogs`, `research_oss`, or `x_major` from the Windmill UI.
Set `example: true` to send the new report’s example before enabling its schedule.
The four retired mixed schedules are explicitly disabled during registration.
It executes collect → rank → persist → deliver; no separate test message is necessary.
The immutable run artifact contains source health, candidates, decisions and model traces.
Scheduled retries resume pending outbox entries first. A crash/timeout during a send
requires manual resolution because Telegram cannot guarantee exactly-once delivery.

## Update and rollback

Copy or pull a tested source revision. Run `deploy-vps.sh` to rebuild only the new
worker, then repeat checks and `register-windmill.py --enable` to reactivate.
Revert to a known-good source revision and rebuild to roll back application code.
Do not reset/delete the data directory or redeploy the shared infrastructure.

To stop ai-dash, disable its four schedules in Windmill and stop only its worker:

```bash
docker stop "$(docker ps -q --filter name=windmill_worker_aidash)"
```

Do not run `docker compose down` on the shared Windmill project.
Back up `/var/code/ai-dash-data` and encrypted secrets independently of daily-dash.
