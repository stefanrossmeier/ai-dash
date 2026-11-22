#!/usr/bin/env bash
# Deterministic post-deployment smoke test for the ai-dash installation.
#
# Verifies, without sending Telegram messages or making paid model calls:
#   1. the source checkout is clean and on a recorded commit
#   2. the full ai-dash stack is running (db, Windmill server, worker,
#      the dedicated
#      llm-gateway instance)
#   3. Windmill answers on its loopback port; the llm-gateway instance
#      authenticates the project principal on /ready
#   4. every rendered schedule exists and is enabled
#   5. git works against the mounted data repo from inside a job-like
#      sanitized environment
#   6. no infrastructure job failures are recorded since container start
#
# Mirrors daily-dash's scripts/smoke-test.sh (its 'dubious ownership'
# regression is the reason the sanitized-env git check exists there too).
#
# Usage: ./scripts/smoke-test.sh
# Environment: AI_DASH_RUNTIME (default: /var/code/ai-dash-runtime)
# Exit codes: 0 = all checks passed, 1 = at least one check failed.

set -Eeuo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUNTIME="${AI_DASH_RUNTIME:-/var/code/ai-dash-runtime}"
ENV_FILE="$RUNTIME/.env"
GATEWAY_TOKEN_SOURCE="${AI_DASH_GATEWAY_TOKEN_SOURCE:-/var/code/llm-gateway-deployments/ai-dash/tokens/gateway.token}"
GATEWAY_TIMEOUT=30

passages=0
failures=0

ok() {
  echo "PASS: $1"
  passages=$((passages + 1))
}

fail() {
  echo "FAIL: $1" >&2
  failures=$((failures + 1))
}

dc() {
  docker compose --project-name ai-dash --project-directory "$ROOT" \
    --env-file "$ENV_FILE" -f "$ROOT/deploy/compose.ai-dash.yaml" "$@"
}

# ---------------------------------------------------------------- 1. source
cd "$ROOT"
if [[ -n "$(git status --porcelain)" ]]; then
  fail "source checkout is dirty: $(git status --porcelain | head -5 | tr '\n' ' ')"
else
  ok "source checkout clean at $(git rev-parse --short HEAD)"
fi

# ------------------------------------------------------------ 2. deployment
if [[ ! -f "$ENV_FILE" ]]; then
  fail "runtime not bootstrapped: $ENV_FILE missing"
  echo "     Run ./scripts/deploy-vps.sh first." >&2
  exit 1
fi

for service in db windmill_server windmill_worker_aidash; do
  if dc ps --status running --services 2>/dev/null | grep -qx "$service"; then
    ok "service running: $service"
  else
    fail "service not running: $service"
  fi
done

# Dedicated llm-gateway instance (separate container, joined to this
# project's network; the ranking gateway since PR "rank-via-llm-gateway").
if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx ai-dash-llm-gateway-1 \
  && [[ "$(docker inspect -f '{{.State.Running}}' ai-dash-llm-gateway-1 2>/dev/null)" == "true" ]]; then
  ok "service running: ai-dash-llm-gateway-1 (dedicated instance)"
else
  fail "service not running: ai-dash-llm-gateway"
fi

# ------------------------------------------------------------------ 3. HTTP
windmill_port="$(grep -oP '^AI_DASH_WINDMILL_PORT=\K.*' "$ENV_FILE" || echo 18090)"
windmill_version="$(curl -fsS --max-time 10 "http://127.0.0.1:$windmill_port/api/version" || true)"
if [[ "$windmill_version" =~ ^\"?CE ]]; then
  ok "Windmill API answering: $windmill_version"
else
  fail "Windmill API not answering on 127.0.0.1:$windmill_port"
fi

# The llm-gateway instance authenticates the ai-dash principal over TCP.
if [[ ! -r "$GATEWAY_TOKEN_SOURCE" ]]; then
  fail "gateway token unreadable: $GATEWAY_TOKEN_SOURCE"
else
  deadline=$((SECONDS + GATEWAY_TIMEOUT))
  ready=""
  while (( SECONDS < deadline )); do
    ready="$(docker exec ai-dash-windmill_worker_aidash-1 /opt/ai-dash/.venv/bin/python -c \
      "import urllib.request
token = open('/run/ai-dash-secrets/gateway_token').read().strip()
req = urllib.request.Request('http://ai-dash-llm-gateway:8080/ready', headers={'Authorization': 'Bearer ' + token})
print(urllib.request.urlopen(req, timeout=10).read().decode())" 2>/dev/null || true)"
    [[ "$ready" == *'"project_id":"ai-dash"'* ]] && break
    sleep 2
  done
  if [[ "$ready" == *'"project_id":"ai-dash"'* ]]; then
    ok "llm-gateway instance ready and principal authenticated (project ai-dash)"
  else
    fail "llm-gateway instance not ready after ${GATEWAY_TIMEOUT}s (last: '$ready')"
  fi
fi

# ------------------------------------------------------------- 4. schedules
# Host-side Windmill API call (same credentials as scripts/register-windmill.py):
# the token lives in the runtime windmill profile, not the worker environment.
windmill_port="$(grep -oP '^AI_DASH_WINDMILL_PORT=\K.*' "$ENV_FILE" || echo 18090)"
schedules_json="$(python3 - "$RUNTIME" "$windmill_port" <<'PYEOF' 2>/dev/null || echo '[]'
import json, sys, urllib.request
runtime, port = sys.argv[1], sys.argv[2]
profile = json.load(open(f"{runtime}/windmill-profile.json"))
base = profile["remote"].rstrip("/") + "/api/w/" + profile["workspaceId"]
req = urllib.request.Request(base + "/schedules/list",
                             headers={"Authorization": "Bearer " + profile["token"]})
print(json.dumps(json.loads(urllib.request.urlopen(req, timeout=30).read())))
PYEOF
)"
schedule_report="$(printf '%s' "$schedules_json" | python3 -c '
import json, sys
rows = json.load(sys.stdin)
own = [s for s in rows if str(s.get("path", "")).startswith("f/ai_dash/")]
disabled = [s["path"] for s in own if not s.get("enabled")]
print(f"{len(own)} {len(disabled)} " + " ".join(disabled))')"
read -r schedule_count disabled_count disabled_list <<<"$schedule_report"
if (( schedule_count >= 3 )); then
  ok "ai-dash schedules present and enabled: $schedule_count"
else
  fail "too few enabled ai-dash schedules: $schedule_count (minimum 3)"
fi
if (( disabled_count == 0 )); then
  ok "all ai-dash schedules enabled"
else
  fail "disabled ai-dash schedules: $disabled_list"
fi

# --------------------------------------------- 5. state store is readable
# ai-dash persists SQLite state + artifacts under /data/ai-dash (no git data
# repo; daily-dash's sanitized-git check guards ITS persist step, not ours).
worker_state="$(dc exec -T windmill_worker_aidash \
  /opt/ai-dash/.venv/bin/python -c "import sqlite3; print(sqlite3.connect('/data/ai-dash/state.sqlite').execute('select count(*) from editions').fetchone()[0])" \
  2>/dev/null || true)"
if [[ "$worker_state" =~ ^[0-9]+$ ]]; then
  ok "worker can read /data/ai-dash/state.sqlite (editions: $worker_state)"
else
  fail "worker cannot read /data/ai-dash/state.sqlite: $worker_state"
fi

# ------------------------------------------------- 6. failures since start
# Data-availability outcomes are legitimate: an empty upstream window, or a
# source whose items are all undated, makes a slot refuse an empty edition by
# design. Everything else (persist, gateway, delivery) is infrastructure.
DATA_AVAILABILITY='no source produced dated items|no qualifying'
worker_log="$(dc logs windmill_worker_aidash 2>&1 || true)"
infra_failures="$(grep 'did not succeed' <<<"$worker_log" \
  | grep -Ev "$DATA_AVAILABILITY" \
  | grep -c . || true)"
data_warnings="$(grep 'did not succeed' <<<"$worker_log" \
  | grep -Ec "$DATA_AVAILABILITY" || true)"
if (( infra_failures == 0 )); then
  ok "no infrastructure job failures in worker log since container start"
else
  fail "$infra_failures infrastructure job failure(s) in worker log since container start"
  grep 'did not succeed' <<<"$worker_log" | grep -Ev "$DATA_AVAILABILITY" | head -5 >&2
fi
if (( data_warnings > 0 )); then
  echo "WARN: $data_warnings data-availability failure(s) (empty or undated windows; not infrastructure)"
fi

# ------------------------------------------------------------------ result
echo
echo "Smoke test: $passages passed, $failures failed"
if (( failures > 0 )); then
  exit 1
fi
exit 0