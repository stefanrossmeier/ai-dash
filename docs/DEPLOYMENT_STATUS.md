# Verified deployment — 2026-11-09

The first report is **AI News**, a mixed-source English AI engineering digest.
No additional report types were added during this rollout.

- VPS: existing `deployment-host` host, source under `/var/code/ai-dash`.
- Dedicated worker: `windmill_worker_aidash`, tag `aidash`.
- Windmill namespace: `f/ai_dash` in the existing workspace.
- Independent bot: `@YOUR_BOT_USERNAME`; destination: private **AI-Dash** channel.
- Credentials and data are outside the public source checkout.
- Daily Berlin slots: 07:30, 12:30, 17:30, 21:30.

## End-to-end evidence

Windmill job `01a1c195-fa9b-d860-8175-0968cf797930` completed successfully.
Run `20261109T183316Z-babd8a10be` persisted its immutable JSON artifact before
sending five Telegram messages. All five have durable `sent` acknowledgements
(message IDs 5–9). The setup connection test was separate (message ID 4).

The run collected 743 dated entries, 119 within 24 hours, and 116 unseen candidates.
Coverage: 49 sources with dated items, 40 empty, four manual benchmark entries,
one unavailable (Reddit), and one without usable dates (Cerebras). All configured
X batches completed; native search is not an exhaustive account timeline.

The initial delivered example contained 30 research papers. This revealed a source
balance issue: the paper feeds dominated the global top-30 selection. The deployed
editorial policy now limits paper stories to six per mixed digest and then fills
remaining space with qualifying non-paper stories. It does not pad with weak or
stale items. The cap is configurable as `max_paper_stories` and has a regression test.
The already-delivered example remains in delivery history so later editions do not
repeat those papers.

The rollout also caught and repaired a model ID-validation failure before delivery.
Ranking now uses short batch-local IDs constrained by the provider response schema;
unknown IDs are rejected and repeated valid decisions are deduplicated.

## Local checks

The complete quality gate passes: 21 tests, Ruff formatting/linting, configuration
validation, generated schedule checks, and source/wheel builds.
No real Telegram sends or model requests occur in the test suite.

Source availability remains visible in each private artifact and the pre-ranking
`collection-latest.json` checkpoint. Individual blocked sources are not reported as
covered. Source provenance and verified endpoint repairs are in [SOURCES.md](SOURCES.md).

# Source-based rollout — 2026-11-09

The mixed digest above is now retired. Its four Windmill schedules remain disabled.
Reports are selected from disjoint source groups in `config/reports.yaml`:

| Report | Sources | Berlin slots | Example result |
| --- | ---: | --- | --- |
| Company & Product Updates | 18 | 07:30, 17:30 | 2 stories, 1 message |
| Blogs & Analysis | 6 | 12:30 | Quiet-day example, 1 message |
| Research & Open Source | 22 | 15:30 | 6 stories, 1 message |
| X — Major AI Labs | 7 | 20:30 | Cached quiet-day example, 1 message |

Examples completed serially through their individual Windmill flows, preserving
existing delivery history. No report ran another report's collector. Research now
has its own paper limit; company/blog/X reports contain no paper feed sources.

Successful example jobs:

- Company: `01a1c1c0-650f-3389-f941-ca86e4cbae45`
- Blogs: `01a1c1c1-99d0-469a-eaac-5fcb19708f6f`
- Research/OSS: `01a1c1c2-b0fb-1e1a-7143-21b73838d0a3`
- X: `01a1c1c3-dab2-30b2-92bf-e667394f8986`

All 45 original X rows are disabled in the base registry. The X profile explicitly
selects seven official lab accounts. It makes at most one application retrieval
request per Berlin calendar day, with at most two posts per account, no paid retry,
and at most one delivered edition per day. SQLite reserves the attempt before any
provider call. Successful results are cached; collect, preview, retries and manual
runs all use the same persistent budget and cache.

Today's X cache was seeded only from the already-paid, validated legacy collection.
It contained zero eligible posts for the seven lab accounts. The new X example
therefore made **zero additional paid retrieval requests** and recorded zero new
retrieval cost. The original larger watchlist is retained only as provenance.

The revised quality gate passes 30 tests, including source separation, persistent
X attempt limits, cached reuse, failure handling, one daily X delivery, report
headers and Windmill positional argument parsing.

## Follow-up overlap crosscheck

The active X list is now three complementary Hermes accounts: `karpathy`,
`fchollet`, and `ArtificialAnlys`. Official lab accounts were removed from paid
retrieval because their blogs or model-release hubs are already configured.
The report is titled **X — AI Leaders & Evaluations**, still at 20:30 Berlin,
with the same daily reservation/cache and delivery limits. Existing same-day
reservations and cached results were preserved; no extra X request was made.

The crosscheck repaired Anthropic's root-path featured-announcement discovery.
VPS verification after deployment: OpenAI 25 dated / 2 fresh entries; Anthropic
7 dated / 2 fresh entries. All five current schedules are enabled. The final
quality gate passes 31 tests, including the newsroom feature regression.

## Paid X acceptance test — failed, schedule paused

The user explicitly authorized one paid X retrieval after the watchlist change.
Exactly one uncached gateway request was made for `karpathy`, `fchollet` and
`ArtificialAnlys`, with one provider attempt and application retries disabled.
Reported cost: $1.03470405; input 27,489 tokens, output 2,212. The provider trace
reported 18 queries, many outside the requested watchlist, and 24 citations.
It returned zero structured posts, so zero posts passed validation.

Generation ID: `redacted-generation-id`.
Private evidence: `/var/code/ai-dash-data/verification/paid-x-20261109/result.json`
and the response cache in that verification directory. The one-shot authorization
marker prevents this verification from being repeated. The production daily budget
was unchanged (file hashes compared before/after). No extra ranking call or Telegram
message was made.

The X schedule is paused and `x_major.enabled` is false, preventing accidental
reactivation during future workspace registration. Company, Blogs and Research/OSS
remain enabled. The integration must be repaired and another paid validation would
require new authorization; this test does not establish successful scoped retrieval.

## Corrected X paid verification accepted — 2026-11-09

The user explicitly authorized one additional paid test of the corrected gateway.
One uncached provider request made exactly one combined query for `karpathy`,
`ArtificialAnlys`, and `fchollet`. It returned ten citation URLs and two fresh
posts by Artificial Analysis. Reported cost: **$0.060482** (8,182 input / 1,177
output tokens). Generation: `redacted-generation-id`.

The two legitimate long-form posts exceeded the old local 700-character cap.
That field now accepts the application's existing 4,000-character content limit.
The original response was replayed without contacting the provider and passed
query, author, URL, citation and rolling 24-hour timestamp checks. The two source
post IDs are `2119878995386982508` and `2119879000713724390`.

The validated response was cached without resetting either request reservation.
A labeled verification example was persisted as
`20261109T204742Z-paid-x-verification` and delivered successfully in one Telegram
message. It uses the saved results and performs no additional ranking/model call.
Private evidence is in `verification/paid-x-fixed-20261109/accepted.json`, alongside
the original failure and replay records.

All five report schedules are enabled, including X at 20:30 Europe/Berlin. The
one-daily-retrieval and one-daily-X-edition guards remain active. The final quality
gate passes 52 tests, including long-form post handling and explicit report pauses.

# Independent runtime rollout — 2026-11-11

The earlier shared-runtime deployment descriptions above are historical. AI Dash
now runs as the standalone Compose project `ai-dash`, using only this repository.
The operational procedure is in [DEPLOYMENT.md](DEPLOYMENT.md), and the complete
coupling audit is in [INDEPENDENCE.md](INDEPENDENCE.md).

- Six independent services: PostgreSQL, Windmill server, orchestration worker,
  AI Dash application worker, ranking gateway and bounded X gateway.
- Own network `ai-dash_default`, database volume `ai-dash_db_data`, worker volumes,
  runtime `.env` and operator profile; own Windmill workspace `ai-dash`.
- Own ranking code/configuration and copied provider credential file. The initial
  upstream key value/account is reused, with independent storage and rotation.
- Windmill binds to loopback port 18090; ranking to 18082; X to 18081.
- All five source-report schedules are enabled with the existing Berlin slots.
- All nine former shared-instance AI Dash schedules are disabled and both retired
  AI Dash containers were removed from that project.

Acceptance evidence:

- Complete quality gate: **60 passing tests**, Ruff lint/format, source/report
  validation, generated workflow checks, source distribution and wheel builds.
- Independent Windmill flow `01a1c905-fea1-91de-332f-3b4625febbd9` succeeded through
  its own orchestrator and `aidash` worker (see private job evidence).
  It verified gateway health, imported the owned gateway implementation, rejected
  legacy service DNS names and read the existing delivery state.
- Telegram preflight confirmed `@YOUR_BOT_USERNAME` has posting permissions in
  the AI-Dash channel. No verification message was sent.
- Delivery history preserved: 11 editions, 16 sent outbox messages, no unresolved sends.
- Real company-source collection returned 292 items across 18 coverage records,
  with zero model traces. No paid model/search request was made during cutover.
- Provider credential validated through the non-billing key endpoint. Ranking
  health also checks that the owned configuration and credential are readable.
- All 10 existing X budget/cache files matched their pre-cutover SHA-256 hashes.
- All 41 daily-dash schedule states and all 19 running containers from other
  projects matched the baseline; none of those containers was recreated.
- Every AI Dash service uses only its own Docker network and has no mount or
  environment reference to daily-dash.
- The full standalone deploy script completed successfully against pushed code
  revision `7f0bb3f`; bootstrap is repeatable and schedules default to disabled.

Private backup and machine-readable evidence:
`/var/code/ai-dash-runtime/migration-20261111/`. This includes the prior source,
application-data archive, old schedule/container baselines, completed smoke-flow
result and `final-verification.json`. Secrets were never added to the repository.

All commits from this rollout use `stefanrossmeier <github@rossmeier.info>` as both
author and committer. The two initially misattributed commits were rewritten with
a guarded force push, and global/repository Git identity settings were corrected.
