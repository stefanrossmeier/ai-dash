# AI Dash news quality and delivery audit — 15 November 2026

## Conclusion

The main failure is **collecting too little usable evidence before selection**. Good
existing sources are reduced to teasers, discovery sources often have no article
text, and trending sources are incorrectly restricted to newly created items.
The ranking policy then rejects precisely those poorly hydrated candidates. This
favors sources with verbose feed summaries, particularly Simon Willison, rather
than reliably finding the most important developments.

There is **no observed one-message delivery limit**. All five production schedules
are enabled. All 32 messages in the production outbox are acknowledged `sent`,
with no pending or uncertain sends. Both parts of the 13 November research edition
were sent, as were both parts of the 10 November afternoon company edition.
Telegram acknowledgement does not prove that a user's client displayed a notification.

This was an investigation: application behavior, production schedules, source
configuration, history and delivery state were not changed. No Telegram messages
or paid model/search requests were made.

## Evidence and scope

Read the repository and inspected production SQLite artifacts in read-only mode,
collection metadata, and the Windmill schedules API. Inspected 27 non-example
persisted editions from 10 November through **15 November, 12:30 Europe/Berlin**;
15 November is an incomplete day. These are persisted editions, not an exhaustive
audit of failed Windmill jobs before persistence.

| Report | Editions | Candidate appearances | Selected stories | Telegram messages | Silent editions |
|---|---:|---:|---:|---:|---:|
| Company | 11 | 120 | 20 | 8 | 4 |
| Blogs | 6 | 29 | 9 | 4 | 2 |
| Research/OSS | 5 | 315 | 23 | 5 | 1 |
| X | 5 | 10 | 7 | 5 | 0 |

Unselected URLs can be reconsidered in successive editions, so candidate
appearances are not all distinct stories. The 32-message all-time outbox count
includes earlier editions/examples; the table covers 22 messages in the audit window.

Daily messages: **6, 5, 4, 4, 2** on 10–14 November, then **1 so far** at the
15 November cutoff. The decline is real; it is not a universal one-message cap.
Normal empty editions deliberately render no message
([presentation.py](../src/ai_dash/presentation.py#L8)).

Evidence files:

- [Sanitized production snapshot](evidence/news-audit-production-2026-11-15.json): counts, per-edition selection, excerpt lengths, coverage and schedule states; no secrets or destinations.
- [Public source probes](evidence/news-audit-sources-2026-11-15.json): 20 endpoints, HTTP status, publication dates, summary/body lengths, advertised feeds and duplicate-feed comparison. These were checked later on 15 November, independently of the production cutoff.
- [Offline reproductions](evidence/news-audit-reproduce.py) and [results](evidence/news-audit-reproductions-2026-11-15.json).

## Findings, in priority order

### 1. P1 — Full feed bodies are silently discarded

[retrieval.py:106](../src/ai_dash/retrieval.py#L106) passes only `entry.summary`
to `make_item`, ignoring `entry.content`, including RSS `content:encoded`.
The checked Latent Space, Interconnects, Ahead of AI and SemiAnalysis feeds each
provided richer content for **all 20 entries**.

Examples from the live probe, measured after stripping markup:

| Source/item | Text currently used | Body already available in feed |
|---|---:|---:|
| Interconnects, “Open-source AI without Jensen” | 43 characters | 8,468 characters |
| AINews, “The No AI Slop Manifesto” | 68 | 23,466 |
| Ahead of AI, “Understanding Positional Embeddings in Modern LLMs” | 53 | 54,947 |
| SemiAnalysis, “Nvidia and the World Without Jensen” | 127 | 26,702 |

The Interconnects item was an actual unselected production candidate at the
15 November cutoff. The Ahead of AI item was published after that cutoff and is
an adapter example, not evidence of a missed story in that production run.

**Repair:** prefer the substantive feed body over a teaser. Extract relevant
sections before applying the current 4,000-character item limit. Simply taking
the first 4,000 characters can retain newsletter introductions and lose later news.
Use only publisher-accessible content; do not infer hidden paywalled text.

### 2. P1 — Discovery supplies no evidence, while the prompt requires evidence

The HN adapter explicitly sets `text = ""`
([retrieval.py:277](../src/ai_dash/retrieval.py#L277)). No linked article fetch follows.
All **77 distinct HN candidates** in the inspected editions had empty text;
**none was selected**. On 14 November, 17 of 19 research candidates were HN links
with empty text; the other two were vLLM release candidates. Selection returned zero.

All **15 HF blog candidate appearances, covering 10 distinct URLs**, also had
empty text. The advertised HF blog feed currently has 907 dated entries but no
summary/body text. HTML discovery immediately returns that feed, without article
hydration. Two empty-text HF appearances were nevertheless selected: evidence
requirements are also inconsistently enforced, rather than safely guaranteed by code.

[editorial.md](../assets/editorial.md) says a title alone is insufficient and
requires a substantive technical fact. The data supplied to ranking frequently
cannot satisfy that instruction. Short Databricks/NVIDIA/OpenAI teasers have a
similar, less absolute disadvantage.

**Repair:** add a bounded article/model-card hydration stage between discovery
and ranking. Preserve article provenance and publication dates separately from
HN submission time. Record `insufficient_evidence` separately from `not_interesting`;
retry missing evidence collection within a small budget. Do not relax factual
standards to compensate for missing text.

### 3. P1 — “Trending” is implemented as “created in the last day”

[retrieval.py:245](../src/ai_dash/retrieval.py#L245) labels a GitHub source
“Trending” but searches `topic:llm created:>DATE stars:>20`. Established repositories
with important new releases or sudden adoption cannot qualify. Only three GitHub
discovery candidates appeared in the entire audit window.

HF trending/author collections use `createdAt` and generate only a generic
repository-creation sentence, without model cards or release evidence
([retrieval.py:286](../src/ai_dash/retrieval.py#L286)). The latest inspected research
edition had 25 dated entries from each configured model hub/trending collection,
but zero fresh entries from those sources. Existing repositories receiving weights,
new revisions or newly relevant community attention are invisible to this policy.

HF papers prefer the original paper's publication timestamp over the daily
curation timestamp ([retrieval.py:284](../src/ai_dash/retrieval.py#L284)). A useful
older paper selected by the community today is discarded by the 24-hour gate.

**Repair:** separate publication, release, update, curation and first-seen times.
Collect tracked releases and meaningful model-card/revision changes, and maintain
popularity snapshots for discovery. Treat “newly trending” explicitly as discovery,
with the original publication date visible; do not relabel old research as new.

### 4. P1 — The daily aggregate is never decomposed into individual news

AINews is one `Item` per newsletter issue. Its linked announcements are never
extracted and verified individually. An issue's teaser can overlap one delivered
announcement while dozens of other developments remain unexamined. Reading its
full body fixes only the first part of this problem.

The supplied 12 November example is an exact match for production run
`20261112T113000Z-fa11fd6532`: nine fresh source entries became seven deduplicated
candidates and two selected Simon Willison stories (scores 69 and 59), delivered
as Telegram message 27. Other candidates included AINews “D-Day”, “The Jev
Revolution”, Simon's Gemini Decisions API analysis, `aws-emulator`, and a tools
index post. The first two had only short descriptions. Gemini Decisions API was
already covered by the morning company edition, so suppressing a duplicate is
plausible. The artifacts do not preserve per-candidate rejection reasons, so the
precise reason for each omission cannot be established retrospectively.

**Repair:** use AINews/TLDR as discovery indexes, extract individual links and
claims, fetch primary evidence, and deduplicate at the announcement level.

### 5. P2 — Six blog source IDs represent only five distinct feed streams

Both `https://latent.space/feeds/all.xml` (smol.ai) and
`https://www.latent.space/feed` returned **the same 20 article URLs**. They are
not complementary news streams. URL deduplication correctly removes double
delivery, but source-count reporting overstates diversity. The P1 smol.ai row
also wins over the P2 Latent Space row, labeling original Latent Space analysis
as an aggregator; all three selected blog stories on 11 November carried that label.

**Repair:** use one canonical publisher stream and classify its entries as
AINews, analysis or podcast from explicit publisher metadata/URLs. Keep provenance
without counting aliases as independent coverage.

### 6. P2 — Strict 24-hour filtering has no recovery path

[models.py:40](../src/ai_dash/models.py#L40) disallows even configuring a window
longer than 24 hours. [processing.py:49](../src/ai_dash/processing.py#L49) drops
every older unseen item. A delayed feed, a failed once-daily edition, or a parser
repair can permanently lose a story. Date-only fields are interpreted as midnight
UTC, shortening the effective opportunity to discover later-published articles.

The current policy is documented, so this is a reliability/design problem rather
than evidence of an accidentally changed setting. Ordinary low publication
frequency alone does not make a correctly dated weekly post miss its publication day.

**Repair:** ingest independently of delivery, retain unseen candidates, and use
per-report watermarks with overlap plus a bounded catch-up period. Suggested
starting point: normal news within 24–48 hours, recovery up to 72 hours, and a
separate weekly analysis queue up to seven days, with dates visible. These are
editorial changes requiring deliberate adoption, not silent timestamp substitution.

### 7. P2 — Important sources are absent or persistently ineffective

Anthropic `/news` does not cover the separate engineering/research streams in
full. Claude Code and Codex release feeds are absent; Cursor's changelog alone
does not provide broad coding-agent coverage. Reddit was unavailable in every
inspected research edition. Cerebras was persistently undated. The manual
benchmark rows are never collected by reports. X is intentionally restricted to
three accounts and two posts per account: all ten accepted candidates in the
audit came from Artificial Analysis, none from Karpathy or Chollet. Native search
is not an exhaustive timeline, so this does not prove those two accounts were inactive.

**Repair:** add missing primary streams below, expose persistent coverage gaps,
and validate dated, content-bearing output. Keep the existing paid X limits.

### 8. P2 — Candidate caps and ranking order can hide stronger stories

Feed parsing keeps at most 25 entries per source before editorial relevance
assessment. The three broad arXiv categories thus contribute at most 75 papers
per run, with source order breaking equal-date ties. The six-paper delivery cap
does not repair omissions earlier in collection. HTML collection returns as soon
as any cards/JSON-LD items exist, skips link fallback, and caps in page order
without sorting; pinned older cards can displace recent ones.

Ranking puts all earlier above-threshold batch decisions into `already_covered`
([processing.py:64](../src/ai_dash/processing.py#L64)), even though final story
and paper caps are applied later. Later, stronger primary evidence can be
suppressed in favor of an earlier batch. Candidates later removed by caps can
still suppress a later representation. This is an order-dependent design risk;
the audit does not quantify actual lost stories from it.

**Repair:** retrieve/sort the relevant window before caps, use topical retrieval
or curated paper discovery, score batches independently, then cluster and select
globally. Do not describe provisional decisions as delivered history.

### 9. P2 — Title-only dedupe can merge unrelated announcements

[processing.py:45](../src/ai_dash/processing.py#L45) deduplicates globally on a
normalized title, even across different publishers/projects. Two unrelated
releases called `v1.0.0` collapse into one. Non-ASCII-only titles can normalize
to an empty string and collide too. This is reproduced for version-only titles;
it is not established as a cause of the supplied example.

**Repair:** prefer canonical URLs and project-scoped release identities, then
cluster actual events with evidence. Generic titles are not universal identities.

### 10. P2 — The current editorial policy measures technical usefulness, not a balanced briefing

The rubric gives technical significance and practical utility 60 of 100 points.
A niche tool patch can pass 55; a useful strategic analysis, explanatory guide or
hands-on follow-up may be excluded for lacking a new announcement. There is no
user-interest profile, source-diversity selection, or explicit “top headlines”
versus “minor tooling updates” distinction. The generic prompt still says
18–30 stories is normal although report maxima are 12/10/12/6.

Some filtering is sensible: `llm 0.37.2` fixes a concrete credential-exposure
issue and is valid news for users of that tool. But it should not substitute for
a broad briefing when discovery is broken. The example's multi-chip claim is
attributed to Anthropic's account; selection of it does not independently verify
the company's performance claim.

**Repair:** allow substantive new analysis without a product launch, distinguish
major developments from specialist updates, and rank using novelty, materiality,
credibility and relevance to the intended reader. Apply a soft source/topic
diversity preference after event deduplication; retain exceptions for genuinely
large releases. Evaluate against a manually judged set of real recent editions.

### 11. P2 — Degradation and model omissions look like quiet success

One dated item from any source is enough for `build` to pass its outage gate
([pipeline.py:29](../src/ai_dash/pipeline.py#L29)). Old items count as source `ok`;
no content-length or critical-source health check exists. All-zero model selection
is accepted. Traces deliberately omit response `content`, so rejected IDs, scores
and reasons are unavailable. Collections fail before writing a checkpoint on a
total outage. There is no operator alert path in this repository for degraded
coverage or suspiciously empty selection.

**Repair:** persist decisions for every candidate with explicit rejection reasons;
record discovered/hydrated/ranked/selected counts; alert an operator on persistent
gaps or a sudden yield collapse while keeping routine quiet editions quiet. Write
failure diagnostics before raising. Do not invent extra consumer news to hide an outage.

### 12. Lower-priority implementation/operations risks

- **Prerelease filter misses `v0.34.0rc4`/`rc3`.** The regex expects `-rc`;
  both slipped into the 14 November research pool. The hard three-release cap
  can let those entries displace stable releases. Reproduced offline.
- **A global uncertain outbox row blocks all reports.** This intentionally avoids
  duplicate sends but needs prompt operator visibility. There are no such rows now;
  it does not explain this audit's missing messages.
- **Registration resets enablement.** `deploy-vps.sh` registers without `--enable`,
  disabling schedules; `--enable-report blogs` also computes false for all others.
  This is an operational trap, not the current cause: all five production schedules
  were confirmed enabled. Preserve existing states on ordinary updates, make
  disabling explicit, and scope report-specific enablement to that report.

## Best source mix for this digest

These are recommendations for an AI engineering reader, based on coverage,
evidence access and demonstrated endpoint behavior—not a universal popularity
ranking. Repair existing ingestion before expanding the source count.

### Keep and repair first

| Source | Best role | Required treatment |
|---|---|---|
| [AINews / Latent Space](https://latent.space/news/) | Broad daily discovery plus AI engineering interviews/analysis | One publisher stream; read full bodies; split roundups into linked events. Both current feeds verified HTTP 200, dated and fully overlapping. |
| [Simon Willison](https://simonwillison.net/) | Hands-on model/API/agent experiments and security/tooling changes | Keep rich excerpts; avoid making small personal-project releases the whole edition. |
| [Interconnects](https://www.interconnects.ai/) | Open-model ecosystem, training and post-training analysis | Use body instead of teaser; make original analysis eligible. Feed verified 200 with richer bodies. |
| [Ahead of AI](https://magazine.sebastianraschka.com/) | Model internals and substantial technical explainers | Lower cadence; analysis queue, not a promised daily headline source. Feed verified 200 with richer bodies. |
| [SemiAnalysis](https://semianalysis.com/) | Compute, inference economics and hardware | Use accessible article/feed evidence and label limitations; feed verified 200 with richer bodies. |
| [Hugging Face blog](https://huggingface.co/blog), official model hubs and tracked OSS releases | Primary model/tool evidence | Hydrate articles/model cards; distinguish publication/release from repository creation. |
| [HF Papers](https://huggingface.co/papers/trending) plus focused arXiv discovery | Research shortlist | Use curation signals and original dates; verify claims; avoid arbitrary first-25 sampling. |

The current source set already contains several of the strongest specialist
publications. Replacing them with generic newsletter lists would leave the main
bug intact.

### Add in this order

| Priority | Source | Why it complements coverage | Integration status at audit |
|---|---|---|---|
| 1 | [Anthropic Engineering](https://www.anthropic.com/engineering) and [Research](https://www.anthropic.com/research) | Primary agent infrastructure, evaluation and research detail absent from the newsroom-only scope | Both pages verified 200; no advertised feed in checked HTML. Build/test dated article adapters; do not assume generic HTML collection covers them. |
| 1 | [Claude Code releases](https://github.com/anthropics/claude-code/releases) and [Codex releases](https://github.com/openai/codex/releases) | Direct evidence for important coding-agent features/fixes | Both `/releases.atom` feeds verified 200 with dates. Filter prereleases robustly and select material changes instead of every patch. |
| 2 | [THE DECODER](https://the-decoder.com/) | Complementary daily reporting beyond the current narrow author/lab set | `https://the-decoder.com/feed/` verified 200 with ten dated entries and useful summaries. Broad topics require relevance filtering; short feed needs more frequent ingestion. |
| 2 | [TLDR AI](https://tldr.tech/ai) | Engineering-focused weekday discovery across models, research and tools | Publisher describes linked source summaries. Landing page verified 200, no feed advertised there. Validate archive ingestion before enabling; landing page alone is not a news adapter. |
| 3 | [Import AI](https://jack-clark.net/) | Research perspective and significance; helpful complement to raw arXiv | `/feed/` verified 200, ten dated entries with full content. Weekly; use an analysis queue and disclose the author's industry perspective. |
| 3 | [Google Research](https://research.google/blog/) and [LangChain](https://www.langchain.com/blog) | Primary research, agents, evaluation and production patterns | Pages verified 200; no feed advertised in checked HTML. LangChain's old blog hostname redirects. Require canonical endpoint/date/content adapter tests and filter vendor promotion. |

Optional broader analysis: [Understanding AI](https://www.understandingai.org/about)
for technical/economic/policy explanations and [One Useful Thing](https://www.oneusefulthing.org/about)
for evidence-based implications for work. Their publisher descriptions support
those roles; automated endpoint behavior was not verified in this audit. They
should be separate analysis inputs, not engineering-release sources.

Do not prioritize famous but currently low-cadence personal blogs as the fix for
daily volume. [Eugene Yan](https://eugeneyan.com/) and [Chip Huyen](https://huyenchip.com/blog/)
have valuable technical work, but their checked feeds' latest dates were June 2026
and January 2025 respectively. Monitor them opportunistically, without counting
them as dependable daily coverage. [The Batch](https://www.deeplearning.ai/the-batch/about)
is a reasonable weekly broad overview; its landing page returned 200 to the
local probe but 403 to the browsing tool and advertised no feed in checked HTML.
Treat integration as unproven until dated issue extraction is tested.

## Recommended implementation sequence and acceptance checks

1. **Recover evidence:** full feed bodies, linked-article hydration and model-card
   evidence. Cache fetches and bound requests/content size. Retain original dates.
2. **Repair discovery:** canonicalize duplicate publisher streams, split curated
   issues into events, and separate creation/update/trending semantics.
3. **Repair selection:** persist accept/reject reasons for every candidate; rank
   independently before global event clustering, caps and diversity preferences.
4. **Improve resilience:** retained unseen queue, bounded catch-up, content-aware
   health reporting, operator alerts and schedule-state preservation.
5. **Add the missing primary and complementary reporting sources above**, only
   after each yields dated, content-bearing items in a shadow collection.

Replay the saved candidate corpus and a manually judged richer-evidence sample.
Measure recall of important developments, unsupported summaries, duplicate events,
topic/source concentration, and cost. Compare the same evidence across candidate
ranking models before changing the cheap model; this audit did not establish that
model choice itself is the root cause. Delivery message count should follow
useful content and Telegram limits, not become a target to fill with weak stories.

The existing **60 tests pass** with
`PYTHONPATH=src .venv/bin/python -m pytest -q` (one existing FastAPI/Starlette
deprecation warning). Five additional offline reproductions confirm the current
full-body loss, prerelease gap, HTML ordering loss, late-item loss and generic-title
collision. They document observed behavior; they are not fixes or a replacement
for regression tests when repairs are implemented.
