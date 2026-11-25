# AI Dash repository map

- Review Scope: full repository architecture refresh
- Doc Status: MAINTAINED
- Last Updated: 2026-11-25T17:17:25Z
- Updated By: agent using [ai-craftkit archdoc](https://github.com/stefanrossmeier/ai-craftkit/blob/ad6f29457e2a1fa43300f34a8f44691251f9c2a2/skills/archdoc/SKILL.md)
- Source Repository: [ai-dash tree](https://github.com/stefanrossmeier/ai-dash/tree/7d61b9161c1894492cba77868f1b6da1d0cffbe3)
- Source Revision: [7d61b9161c1894492cba77868f1b6da1d0cffbe3](https://github.com/stefanrossmeier/ai-dash/commit/7d61b9161c1894492cba77868f1b6da1d0cffbe3)
- Source Basis: README, AGENTS, manifests, modules, configuration, workflows, CI, tests and build scripts.

Unless marked otherwise, implementation descriptions below are **verified** against
this revision. This is repository evidence, not a claim about live deployment.

Deployment and publication checks have their own scope in the
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

## Entry points and evidence

The installed `ai-dash` command is `cli.main`, declared in [pyproject.toml](https://github.com/stefanrossmeier/ai-dash/blob/7d61b9161c1894492cba77868f1b6da1d0cffbe3/pyproject.toml).
Windmill enters through [workflows/windmill/f/ai_dash/run_digest.sh](https://github.com/stefanrossmeier/ai-dash/blob/7d61b9161c1894492cba77868f1b6da1d0cffbe3/workflows/windmill/f/ai_dash/run_digest.sh),
which sets checkout/runtime defaults before calling `ai-dash run --report ID`.
The package is an application/worker, not a supported general-purpose Python API.

Navigation evidence: [src/ai_dash](https://github.com/stefanrossmeier/ai-dash/tree/7d61b9161c1894492cba77868f1b6da1d0cffbe3/src/ai_dash), [config](https://github.com/stefanrossmeier/ai-dash/tree/7d61b9161c1894492cba77868f1b6da1d0cffbe3/config), [assets](https://github.com/stefanrossmeier/ai-dash/tree/7d61b9161c1894492cba77868f1b6da1d0cffbe3/assets), [deploy](https://github.com/stefanrossmeier/ai-dash/tree/7d61b9161c1894492cba77868f1b6da1d0cffbe3/deploy), [scripts](https://github.com/stefanrossmeier/ai-dash/tree/7d61b9161c1894492cba77868f1b6da1d0cffbe3/scripts), [tests](https://github.com/stefanrossmeier/ai-dash/tree/7d61b9161c1894492cba77868f1b6da1d0cffbe3/tests).

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

Contributor and agent guidance is in `AGENTS.md` and `CONTRIBUTING.md`; both
retain actual contributor authorship and are included in the reviewed source export. These guides describe implementation and do not establish
historical decision approval or permission for external actions.

## Verification and reading order

The [scripts/check.sh](https://github.com/stefanrossmeier/ai-dash/blob/7d61b9161c1894492cba77868f1b6da1d0cffbe3/scripts/check.sh) gate is defined alongside the
[CI workflow](https://github.com/stefanrossmeier/ai-dash/blob/7d61b9161c1894492cba77868f1b6da1d0cffbe3/.github/workflows/ci.yml). Key-free checks require
Python 3.12+ and `uv`; Linux/macOS locking uses POSIX `fcntl`. [pyproject.toml](https://github.com/stefanrossmeier/ai-dash/blob/7d61b9161c1894492cba77868f1b6da1d0cffbe3/pyproject.toml)
and `uv.lock` define Python packaging/dependencies. The source archive is checked
against [publication-files.txt](https://github.com/stefanrossmeier/ai-dash/blob/7d61b9161c1894492cba77868f1b6da1d0cffbe3/publication-files.txt); `AGENTS.md` and the evolution guide
are public-safe inputs, while dated operational dossiers are excluded.

Representative regressions: [tests/test_cadence.py](https://github.com/stefanrossmeier/ai-dash/blob/7d61b9161c1894492cba77868f1b6da1d0cffbe3/tests/test_cadence.py), [tests/test_fresh_delivery.py](https://github.com/stefanrossmeier/ai-dash/blob/7d61b9161c1894492cba77868f1b6da1d0cffbe3/tests/test_fresh_delivery.py), [tests/test_community_policy.py](https://github.com/stefanrossmeier/ai-dash/blob/7d61b9161c1894492cba77868f1b6da1d0cffbe3/tests/test_community_policy.py), [tests/test_gateway_client.py](https://github.com/stefanrossmeier/ai-dash/blob/7d61b9161c1894492cba77868f1b6da1d0cffbe3/tests/test_gateway_client.py), [tests/test_network_security.py](https://github.com/stefanrossmeier/ai-dash/blob/7d61b9161c1894492cba77868f1b6da1d0cffbe3/tests/test_network_security.py), [tests/test_status.py](https://github.com/stefanrossmeier/ai-dash/blob/7d61b9161c1894492cba77868f1b6da1d0cffbe3/tests/test_status.py), [tests/test_public_export.py](https://github.com/stefanrossmeier/ai-dash/blob/7d61b9161c1894492cba77868f1b6da1d0cffbe3/tests/test_public_export.py).
They establish bounded contracts, not live source availability or model quality.

Read the README and this map first, then [architecture](ARCHITECTURE.md), the
relevant [interface](API_SURFACE.md), and [operations](OPERATIONS.md). The
[evolution guide](../EVOLUTION.md) explains historical claims and corrections.
**Missing:** accepted architecture decision records; do not infer approved
historical rationale from the current module layout.
