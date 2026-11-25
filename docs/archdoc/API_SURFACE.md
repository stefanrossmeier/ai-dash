# AI Dash interfaces

Reviewed 25 November 2026. The application exposes a CLI, versioned configuration,
private artifacts and integration clients. It does not serve an application HTTP API.

## CLI

The `ai-dash` entry point is `ai_dash.cli:main`. Output is JSON on stdout; preview
also renders messages to stderr. Configuration/runtime errors return exit code 1.

| Command | Effect |
| --- | --- |
| `validate` | Validate source/report configuration and print counts; no source requests |
| `collect --report ID` | Retrieve sources and coverage; no model inference or delivery |
| `preview --report ID` | Build and render without delivery-history writes; inference can cost money |
| `run --report ID` | Lock state, collect/build, persist, then deliver; inference can cost money |
| `status` | Inspect report health and edition/outbox counts |
| `check-telegram` | Check bot, channel and posting permission without sending |
| `resolve-delivery --run-id ID --part N --resolution sent\|pending` | Resolve a still-`sending` outbox entry manually |

Common options: `--config`, `--reports`, `--prompt`, `--data-dir`, `--gateway-url`,
`--output`, `--no-x` and `--example`. `--run-id` identifies a delivery-resolution
record; inference identity is supplied through `AI_DASH_RUN_ID` or Windmill job
environment, not that flag. `--example` can send an otherwise quiet report when
used with `run`.

`resolve-delivery` cannot modify already-discarded rows. Marking a still-uncertain
row pending does not authorize the next `run` to replay it: fresh-only processing
discards old unsent rows. Inspect the channel before resolving uncertainty.

## Configuration and secrets

`Source`, `Settings`, `Report` and `YouTubeChannel` are strict Pydantic models;
unknown configuration fields fail validation. Report source references and unique
IDs are checked. Slots use `HH:MM` in the configured timezone. A report has no
independent `freshness_hours` override: its window follows its slots. Source-level
settings still support a freshness value for direct internal collection.

`AI_DASH_HOME` locates checkout assets. `AI_DASH_DATA_DIR` locates private state.
Telegram and gateway credentials support private `_FILE` settings; direct token
environment values are also supported by the CLI/client. Reddit uses three
private regular files and checks permissions, symlinks and length. Prefer files
over shell history, command arguments or copied runtime configuration.

## Gateway and orchestration

The client uses authenticated `POST /v1/chat` and, after a lost response,
`GET /v1/requests/{id}?format=dashboard`. Each payload includes durable run identity;
the canonical payload hash forms its `Idempotency-Key`. Successful content must be
an object. HTTP errors report status/request identity without raw upstream text.
Only recognized input-limit error codes permit safe splitting.

Default standalone gateway URL: `http://127.0.0.1:18182`. The worker uses its owned
internal DNS URL and mounted project bearer. `/ready` and `/v1/usage` belong to the
gateway, not this application. Model aliases and provider policies are external.

Windmill runs `f/ai_dash/run_digest` with positional `report` and `example` inputs.
Generated flows and schedules use the `aidash` worker tag and prevent overlap per
flow. The application lock also serializes reports sharing a state directory.
Registration only upserts the application namespace and preserves enablement.

## Artifacts and delivery

`Artifact` schema version 1 includes report/run identity, creation/window times,
stories, candidates, coverage, traces, stats, selection logs and health warnings.
Fields are strict; old artifacts remain readable through defaults for added fields.
Coverage distinguishes ok, empty, unavailable, undated, manual, disabled and
search-required states. Timestamp basis separates publication, submission,
curation and repository updates. Items can retain a `linked_url` for primary
article hydration while their canonical Reddit discussion URL and submission
timestamp remain unchanged.

SQLite outbox states include `pending`, `sending`, `sent`, `discarded` and
`discarded_uncertain`. JSON artifacts do not include the destination, but SQLite
edition records do; keep the entire state directory private. Gateway metadata and
source excerpts are also operational data, not automatically sanitized exports.

Presentation uses plain text, disables link previews and splits at story
boundaries below Telegram's UTF-16 budget. Telegram retries explicit 429 rejection
within bounds; transport uncertainty is not blindly retried. Bot API URLs contain
the bot token and must never be copied into logs or public evidence.
