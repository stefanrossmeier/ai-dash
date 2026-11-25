# AI Dash architecture

- Review Scope: delta — published history, provenance and evidence-link refresh
- Doc Status: MAINTAINED
- Last Updated: 2026-11-25T17:49:49Z
- Updated By: agent using [ai-craftkit archdoc](https://github.com/stefanrossmeier/ai-craftkit/blob/ad6f29457e2a1fa43300f34a8f44691251f9c2a2/skills/archdoc/SKILL.md)
- Source Repository: [ai-dash tree](https://github.com/stefanrossmeier/ai-dash/tree/f5fd37128a569a908f31f21e2ae07047ea25b4cf)
- Source Revision: [f5fd37128a569a908f31f21e2ae07047ea25b4cf](https://github.com/stefanrossmeier/ai-dash/commit/f5fd37128a569a908f31f21e2ae07047ea25b4cf)
- Source Basis: instruction and contribution requirements, domain/CLI/pipeline modules, adapters, storage, deployment and boundary regressions.

Unless marked otherwise, implementation descriptions below are **verified** against
this revision. Source Revision identifies the inspected source snapshot, before
this documentation update. This is repository evidence, not a claim about live deployment.

AI Dash owns AI-news acquisition, editorial selection,
private report artifacts and Telegram delivery. Windmill schedules and executes
jobs. A separately deployed project-owned LLM Gateway owns provider execution,
credentials, accounting and recovery. There is no application web dashboard or
inbound application API.

## Context and system boundary

| External actor/system | Relationship and protocol |
| --- | --- |
| Operator | Configures policy and private runtime; invokes the CLI or deploys workflows |
| Windmill | Executes application commands via scheduled jobs; owns orchestration state |
| Public publishers, Nitter, YouTube, code/model hubs | HTTP(S) feed/API/article inputs; publishers remain authoritative for their content |
| Reddit | Fixed OAuth/token and listing API over HTTPS using private application credentials |
| Owned LLM Gateway | Authenticated HTTP chat/recovery; owns provider execution, keys and accounting |
| Telegram and readers | Bot API over HTTPS; acknowledged parts are the application's delivery evidence |

Internal collection, editorial selection, artifact/outbox persistence and Telegram
transport belong to AI Dash. Windmill and the gateway have independent lifecycles;
ordinary Python packages are in-process dependencies, not external services.
Evidence: [src/ai_dash/cli.py](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/src/ai_dash/cli.py), [src/ai_dash/retrieval.py](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/src/ai_dash/retrieval.py), [src/ai_dash/reddit.py](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/src/ai_dash/reddit.py), [src/ai_dash/gateway.py](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/src/ai_dash/gateway.py), [src/ai_dash/delivery.py](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/src/ai_dash/delivery.py), [deploy/compose.ai-dash.yaml](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/deploy/compose.ai-dash.yaml).

## Drivers, constraints and strategy

Explicit current requirements in [AGENTS.md](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/AGENTS.md) and
[CONTRIBUTING.md](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/CONTRIBUTING.md) include runtime independence, private credentials,
inspectable source evidence, persistence before delivery and retaining accounting
history. These drive separate service ownership, structured records and a durable
outbox. They do not establish an availability or factual-accuracy guarantee.

Hard implementation constraints are Python 3.12+, POSIX file locking, a single
shared SQLite state directory, Telegram message size/acknowledgement semantics,
Windmill's job environment and a separately authenticated gateway. See
[pyproject.toml](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/pyproject.toml), [src/ai_dash/storage.py](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/src/ai_dash/storage.py) and
[src/ai_dash/presentation.py](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/src/ai_dash/presentation.py). Component licensing is a separate
constraint in [third-party notices](../../THIRD_PARTY_NOTICES.md).

The solution strategy is a CLI-composed pipeline with bounded acquisition,
evidence enrichment, model decisions constrained by deterministic policy, then
immutable artifacts and an outbox. This describes implementation; **missing:**
accepted ADRs establishing historical rationale for the technology choices.


## Building blocks, dependency direction and interactions

`cli.py` validates source/report configuration and composes adapters. `reports.py`
selects each report's sources and policies; `cadence.py` derives the preceding
scheduled interval plus overlap in its configured timezone. Collection produces
strict `Item` and `Coverage` records. Article hydration enriches bounded evidence
and verifies linked publication dates without inventing missing dates. Reddit
retains authenticated discussion/crosspost text and hydrates external primary
links without changing the discussion identity or submission timestamp. Its own
editorial prompt admits worthwhile community discussion and attributed claims;
it does not require every post to independently establish a scientific result.

Model-backed reports deduplicate recent/history items, require evidence, evaluate
bounded candidate batches, apply deterministic impact gates, consolidate events,
apply caps and summarize only finalists. Schema/ID checks reject missing or
invented candidate slots. The YouTube branch lists dated uploads newest first
without hydration or LLM inference; it deliberately ignores delivery history to
show the rolling window again.

`pipeline.run` holds an exclusive process lock, discards old unsent outbox entries,
checks Telegram posting permission and builds a fresh artifact. Persistence writes
and fsyncs an immutable JSON file before inserting the edition/outbox in SQLite.
Delivery only follows persistence. A failed send discards its unsent parts and
fails the run; the next run collects again. Date windows, scores, coverage,
selection reasons and model traces remain in private artifacts/checkpoints.

`cli` composes policy, gateway, Telegram and storage adapters; `pipeline` calls
collection, hydration, processing, presentation and storage. `processing` calls
ranking/gateway, while transport/storage modules do not import CLI composition.
Domain models are shared contracts. Source adapters return data rather than
sending messages; only the persisted outbox enters delivery. Evidence:
[src/ai_dash/cli.py](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/src/ai_dash/cli.py), [src/ai_dash/pipeline.py](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/src/ai_dash/pipeline.py), [src/ai_dash/processing.py](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/src/ai_dash/processing.py), [src/ai_dash/models.py](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/src/ai_dash/models.py).
Detailed contract ownership is in [interfaces](API_SURFACE.md); deployment and
recovery procedures belong to [operations](OPERATIONS.md).

## State and ownership

| State | Owner and invariant |
| --- | --- |
| Source/report/prompt files | Versioned application policy; no credential values |
| SQLite `editions` and `outbox` | Private state; WAL/full synchronization; delivery status retained |
| JSON artifacts | Exclusive-create immutable output; never used as a public data feed automatically |
| Collection checkpoints | Replaceable private diagnostics, including failed selection evidence |
| Gateway receipts/ledger | Independent gateway deployment; never reset to regain allowance |
| Windmill database/volumes/profile | Application-owned scheduling and operation state |
| Telegram and Reddit credentials | Independent private file mounts; not provider credentials |

Publishers own source assertions; model outputs and collection caches are
transient inputs until captured in a private artifact/checkpoint. AI Dash owns
its selection and delivery records, not upstream facts. Gateway and Windmill state
are authoritative in their services, not reconstructible from the application
SQLite file. State evidence: [src/ai_dash/storage.py](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/src/ai_dash/storage.py),
[src/ai_dash/pipeline.py](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/src/ai_dash/pipeline.py) and [deploy/compose.ai-dash.yaml](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/deploy/compose.ai-dash.yaml).

An artifact file can survive a subsequent failed SQLite insert as an orphan; file
and database writes are not a distributed transaction. The lock and SQLite model
support a single writer/instance, not distributed active-active operation.

## Cross-cutting validation, trust and network boundaries

All external content and model output are untrusted data. Models return structured
decisions and text; they do not execute shell commands or acquire authority to
read credentials. Pydantic/slot checks constrain structure, while deterministic
policy constrains admission. These do not establish factual truth or immunity to
prompt injection that changes editorial judgment.

Public-source fetching pins checked global IPs and validates redirects, preserving
Host and TLS identity. It rejects credentials in fetch URLs, private/mixed DNS
answers, nonstandard ports and compressed response bodies; streaming bounds limit
source/article evidence. This transport carries no provider, Telegram or Reddit
credentials. Authenticated service clients retain fixed-service boundaries.
Telegram errors omit bot-token URLs, and HTTP client logs are reduced at the CLI.

Windmill runs the application worker as root in the current image. It mounts only
needed application state and secrets, but this is not a general sandbox for
untrusted jobs or multi-tenant use. The gateway is an independent service boundary;
separate upstream keys are needed for independent revocation/billing.

## Constraints and remaining risks

Nitter and public publishers can fail, truncate feeds, change layouts or serve
misleading material. Coverage records expose gaps; they do not prove exhaustive
collection. Ranking is subjective and does not independently fact-check sources.
There is no end-user UI, hosted multi-user service or built-in feedback loop.

Exactly-once Telegram delivery is impossible across a lost acknowledgement. An
uncertain send is retained as `discarded_uncertain`; some stories may already have
reached Telegram. History currently reserves every story of an edition with at
least one acknowledged part, so an unsent part of a partial edition can suppress
its stories until the history window expires. This behavior remains explicit and
is not a claim of per-story delivery recovery.

Gateway recovery uses stable run/request identities. Only explicit pre-dispatch
input-limit rejection permits ranking/summary batch splitting. Unknown provider
outcomes retain their identity and are not treated as permission to spend again.

## Enforced invariants and remaining evidence gaps

| Current invariant | Concrete evidence |
| --- | --- |
| Reject unknown config/model fields and invented/missing ranking slots | [src/ai_dash/models.py](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/src/ai_dash/models.py); [tests/test_pipeline.py](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/tests/test_pipeline.py) |
| Serialize shared-state runs; persist before sending; never replay old unsent news | [src/ai_dash/storage.py](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/src/ai_dash/storage.py); [tests/test_fresh_delivery.py](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/tests/test_fresh_delivery.py) |
| Pin checked public addresses, validate redirects and bound response bodies | [src/ai_dash/network.py](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/src/ai_dash/network.py); [tests/test_network_security.py](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/tests/test_network_security.py) |
| Retain request identity after unknown inference outcomes; split only explicit pre-dispatch input limits | [src/ai_dash/gateway.py](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/src/ai_dash/gateway.py); [tests/test_input_limits.py](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/tests/test_input_limits.py) |
| Keep selection and acknowledgement outcomes distinct | [src/ai_dash/storage.py](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/src/ai_dash/storage.py); [tests/test_status.py](https://github.com/stefanrossmeier/ai-dash/blob/f5fd37128a569a908f31f21e2ae07047ea25b4cf/tests/test_status.py) |

The [evolution guide](../EVOLUTION.md) identifies old defects and requirement
changes without recasting commits as accepted ADRs. **Missing:** an agreed service
level objective, systematic real-news ranking evaluation, a separate operator
alert route and an end-to-end restore drill. **Unresolved:** image advisory backlog,
non-root execution validation and upstream derived-image terms; see
[publication review](../PUBLICATION.md). Offline tests do not close those gaps.
