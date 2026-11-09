#!/usr/bin/env bash
# Run ON the existing Windmill VPS, after copying this independent checkout there.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUNTIME="${WINDMILL_RUNTIME:-/var/code/daily-dash-windmill-local}"
export AI_DASH_SOURCE="$ROOT"
export AI_DASH_DATA_SOURCE="${AI_DASH_DATA_SOURCE:-/var/code/ai-dash-data}"
export AI_DASH_SECRETS_SOURCE="${AI_DASH_SECRETS_SOURCE:-/var/code/ai-dash-runtime/secrets}"
install -d -m 700 "$AI_DASH_DATA_SOURCE" "$AI_DASH_SECRETS_SOURCE"
# Existing project name/network/DB; scope mutation to the NEW worker only.
docker compose --project-directory "$RUNTIME" \
  --env-file "$RUNTIME/.env" \
  -f "$RUNTIME/docker-compose.yml" \
  -f "$RUNTIME/docker-compose.override.yml" \
  -f "$ROOT/deploy/compose.ai-dash.yaml" \
  up -d --build --no-deps windmill_worker_aidash ai_dash_x_gateway
python3 "$ROOT/scripts/register-windmill.py"
