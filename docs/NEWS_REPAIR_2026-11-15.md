# News selection repair — 15 November 2026

The [audit](NEWS_AUDIT_2026-11-15.md) found that successful Telegram delivery was
being fed a weak candidate pool. This change repairs evidence collection and
selection rather than targeting a message quota.

## Behavior changes

- Feed parsing prefers full RSS/Atom bodies over descriptions. Bounded excerpts
  retain the beginning, middle and end of long material instead of only introductions.
- Thin articles and model cards are fetched from public endpoints with bounded
  requests, timeouts, redirects, response size and content types. Each redirect is
  checked against private/local addresses and credentialled URLs. Evidence failures
  preserve the original text and become explicit diagnostics.
- AINews issues can yield up to eight external linked discoveries. These require a
  publisher publication date from article hydration before entering selection. Old
  or undated linked material cannot borrow the issue's date. The date gate runs again
  after hydration.
- Configured URL queries are preserved. The old unconditional `params={}` stripped
  Hugging Face author/sort/limit filters; live collection of the Qwen source returned
  other organizations' models. A regression covers this newly discovered bug.
- GitHub discovery searches recent pushes, including established projects. Model
  hubs use modification timestamps and fetched cards. HF paper curation preserves
  both the curation date and original paper publication date. These signals are
  explicitly labelled and cannot establish a new release alone.
- Date-only publication values remain actual source dates. Catch-up is bounded to
  48 hours for company news, 72 for research/OSS and seven days for analysis. X keeps
  24 hours. Telegram stories show the timestamp and its basis.
- Dedupe retains richer evidence for identical URLs and does not merge unrelated
  version-only or non-Latin titles. HTML collection combines dated cards with
  remaining link discovery, sorts by publication date, then applies its cap.
  Stable releases are not displaced by `rc` versions without a hyphen.
- Every evidenced candidate receives a ranking decision and reason. Missing
  decisions fail visibly; rejected decisions are persisted. Batch decisions are
  never passed off as delivered history. A global event comparison chooses the
  strongest representative before caps; substantial new analysis stays eligible.
- A soft diversity preference spreads near-peer stories across publishers after
  three stories from a publisher, retaining major (85+) stories and backfilling
  from qualifying material if necessary. It creates no minimum story count.
- Artifacts/checkpoints record hydration, evidence gaps, scores, event duplicates
  and cap exclusions. Total-outage checkpoints survive failure. `status` exposes
  latest report health and run results/logs expose warnings.
- Ordinary registration preserves schedule enablement. Enabling or pausing one
  report leaves others unchanged; fresh schedules remain disabled until rollout.

## Sources

One canonical Latent Space / AINews feed replaces two identical active streams.
Six additions: Anthropic Engineering and Research, official Claude Code and Codex
release feeds, THE DECODER and Import AI. Source IDs remain report-specific and
the original registry is retained as provenance. The archived alias does not count
as independent coverage.

[Public smoke evidence](evidence/news-repair-source-smoke-2026-11-15.json) checks
collection/hydration without models, X or Telegram. In the checked samples,
Interconnects now supplies 8,468 characters; the HF robot simulation and XYBench
articles supply 11,012 and 8,228 characters instead of empty text. Anthropic's
engineering/research pages produce dated articles with substantial hydrated text.
The Claude Code and Codex collectors select stable releases from their real feeds.

## Verification

The test suite covers feed body recovery, later sections, release filtering,
combined HTML discovery, roundup dates/budgets, article/model-card evidence,
private-address and redirect rejection, response-size limits, source query
preservation, discovery timestamps, generic-title collisions, missing model output,
global event comparison, publisher diversity, failure checkpoints, diagnostics,
catch-up dates, schedule preservation and multipart delivery/history.

Validation: repository quality gate (`./scripts/check.sh`), including **100 passing tests**,
Ruff, source/report validation, generated workflow consistency and source/wheel
builds. Public endpoint results are point-in-time checks; they do not guarantee
future availability.

The local macOS environment requires `PYTHONPATH=src` because Python skips its
hidden editable-install `.pth` file. CI runs the normal clean-install quality gate.

The baseline offline audit probe now prints false for repaired behaviors. Its
original saved JSON remains historical evidence; regression tests assert desired
behavior going forward.

## Operational limits

This PR does not deploy the VPS or send a validation message. Existing database,
history, outbox, independent services and X budgets are retained. Additional
ranking-model work is one cheap consolidation request when multiple stories qualify;
larger evidence/catch-up windows also increase ranking input. No paid acceptance
run was made during this repair.

Catch-up is a bounded lookback, not a continuously polled durable discovery queue.
Very short publisher feeds can still require more frequent ingestion to avoid
missed items between daily editions. TLDR's archive integration, a notification
destination for operator health alerts, and popularity-change snapshots remain
future work. Status and structured diagnostics make current gaps inspectable;
blocked Reddit or other inaccessible publishers are not silently treated as covered.
