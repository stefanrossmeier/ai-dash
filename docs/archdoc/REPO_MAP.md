# AI Dash repository map

Reviewed 25 November 2026 against the application integrated in PR 29 and the
documentation/checker follow-up. This describes repository behavior; live
deployment and publication checks are scoped separately in the
[publication review](../PUBLICATION.md).

AI Dash is a Python 3.12+ application for scheduled Telegram briefings. Start with
the [README](../../README.md), [architecture](ARCHITECTURE.md), then the
[interface](API_SURFACE.md) or [operations](OPERATIONS.md) relevant to your change.

| Path | Responsibility |
| --- | --- |
| `src/ai_dash/cli.py` | CLI parsing, configuration, secret references and command composition |
| `models.py`, `reports.py`, `cadence.py` | Strict domain/configuration models, source membership and retrieval windows |
| `retrieval.py`, `content.py`, `network.py` | Collection adapters, article evidence and bounded public-network transport |
| `reddit.py` | Fixed-service Reddit OAuth with private credential files |
| `gateway.py` | Authenticated inference identity and request recovery |
| `ranking.py`, `processing.py` | Scoring gates, model stages, deduplication, event grouping and caps |
| `pipeline.py` | Collection through persistence and delivery orchestration |
| `storage.py` | SQLite history/outbox, immutable JSON artifacts and the process lock |
| `presentation.py`, `delivery.py` | Plain-text message rendering and Telegram transport |
| `config/` | Source registry, report policies/slots and YouTube channels |
| `assets/` | Default, X-specific and Reddit-community ranking prompts |
| `workflows/windmill/` | Versioned scripts, seven flows and twelve schedules |
| `scripts/` | Validation, workflow rendering, runtime provisioning, registration and smoke checks |
| `deploy/` | Application worker image and independently owned Compose stack |
| `tests/` | Offline behavior, fault, source, network and gateway regressions |
| `docs/evidence/` | Dated source/selection evidence, not current runtime state |

Private runtime directories own secrets, the Windmill profile, database and report
state. Local `var/`, `dist/`, virtual environments and caches are ignored outputs.
They are not publication inputs. The wheel contains application code; deployment
also requires the checkout's configuration, prompts and workflows.

## Commands and generated files

```sh
uv sync --frozen --no-editable
./scripts/check.sh
uv run --no-sync python scripts/render-windmill.py --check
```

`scripts/check.sh` runs Ruff, offline tests, CLI configuration validation, generated
workflow checks and package builds. It does not invoke the VPS, send Telegram
messages or run paid inference. The separate CI job scans history and checkout
with Gitleaks. The gate reinstalls the current package without editable path
hooks, then uses `uv run --no-sync` so later commands do not switch installations.

Edit report slots in `config/reports.yaml`; regenerate workflow YAML with
`uv run --no-sync python scripts/render-windmill.py`. Generated schedules remain disabled in
source. Registration owns runtime enablement and preserves existing settings.
The Hermes importer reconstructs an old registry snapshot and overwrites the live
source file; it is not an additive synchronization command.

The operational checkout uses `AGENTS.md` for owner-specific instructions; that
file is omitted from the clean source export. Public contribution guidance is in
`CONTRIBUTING.md`. These guides describe implementation and do not establish
historical decision approval or permission for external actions.
