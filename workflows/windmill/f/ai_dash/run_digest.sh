#!/usr/bin/env bash
set -Eeuo pipefail
# Windmill discovers positional arguments from these exact assignments.
report="$1"
example="$2"
export AI_DASH_HOME="${AI_DASH_HOME:-/opt/ai-dash}"
export AI_DASH_DATA_DIR="${AI_DASH_DATA_DIR:-/data/ai-dash}"
export AI_DASH_X_GATEWAY_URL="${AI_DASH_X_GATEWAY_URL:-http://ai_dash_x_gateway:8080}"
# Ranking routes to ai-dash's dedicated llm-gateway instance. Windmill jobs run
# a sanitized environment, so the migrated worker env never reaches the job;
# this default is what scheduled flows actually use. The Bearer token is read
# by the client from the token file mounted into the worker.
export AI_DASH_GATEWAY_URL="${AI_DASH_GATEWAY_URL:-http://ai-dash-llm-gateway:8080}"
export AI_DASH_GATEWAY_TOKEN_FILE="${AI_DASH_GATEWAY_TOKEN_FILE:-/run/ai-dash-secrets/gateway_token}"
export AI_DASH_TELEGRAM_TOKEN_FILE="${AI_DASH_TELEGRAM_TOKEN_FILE:-/run/ai-dash-secrets/telegram_token}"
export AI_DASH_TELEGRAM_CHAT_ID_FILE="${AI_DASH_TELEGRAM_CHAT_ID_FILE:-/run/ai-dash-secrets/telegram_chat_id}"
args=(run --report "$report")
case "$example" in true|True|1) args+=(--example) ;; esac
"$AI_DASH_HOME/.venv/bin/ai-dash" "${args[@]}" > result.json
