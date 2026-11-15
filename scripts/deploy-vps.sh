#!/usr/bin/env bash
# Run on the VPS from ai-dash's own source checkout.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export AI_DASH_RUNTIME="${AI_DASH_RUNTIME:-/var/code/ai-dash-runtime}"
export AI_DASH_SOURCE="$ROOT"
export AI_DASH_DATA_SOURCE="${AI_DASH_DATA_SOURCE:-/var/code/ai-dash-data}"
export AI_DASH_SECRETS_SOURCE="${AI_DASH_SECRETS_SOURCE:-$AI_DASH_RUNTIME/secrets}"
install -d -m 700 "$AI_DASH_DATA_SOURCE" "$AI_DASH_SECRETS_SOURCE"
python3 "$ROOT/scripts/init-runtime.py"
for secret in openrouter_api_key telegram_token telegram_chat_id; do
  test -s "$AI_DASH_SECRETS_SOURCE/$secret" || {
    echo "Missing ai-dash secret: $AI_DASH_SECRETS_SOURCE/$secret" >&2
    exit 1
  }
done
docker compose --project-name ai-dash --project-directory "$ROOT" \
  --env-file "$AI_DASH_RUNTIME/.env" -f "$ROOT/deploy/compose.ai-dash.yaml" \
  build windmill_worker_aidash
docker compose --project-name ai-dash --project-directory "$ROOT" \
  --env-file "$AI_DASH_RUNTIME/.env" -f "$ROOT/deploy/compose.ai-dash.yaml" \
  up -d --wait --wait-timeout 300
python3 "$ROOT/scripts/bootstrap-windmill.py"
# New schedules default to disabled; updates preserve existing enablement.
python3 "$ROOT/scripts/register-windmill.py"
