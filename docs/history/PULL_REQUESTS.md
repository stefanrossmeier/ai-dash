# Historical pull-request descriptions

These are the 33 original pre-publication PR titles and descriptions, retained
as development evidence. They are dated claims, not current guarantees. Commit
links/identifiers target the corresponding sanitized history where available.
The original GitHub PR records and CI logs remain private; there were no PR reviews
or issue/review comments in the inspected records. Native PR refs and cached diffs
are deliberately not migrated. See [history sanitization](../HISTORY_SANITIZATION.md).

<a name="pr-1"></a>

## PR 1: Repair news collection, selection quality and source coverage

Author: `stefanrossmeier`. Opened: 2026-11-15T13:30:18Z. Merged: 2026-11-15T13:31:25Z.

Sanitized merge: [622db3b8ffca](https://github.com/stefanrossmeier/ai-dash/commit/622db3b8ffca48c0048f27a1739a51964902d4dd).

### Original description

AI Dash was selecting from teasers and empty excerpts while requiring substantive technical evidence. It also stripped configured URL filters, treated repository creation as trending news, and could suppress stronger stories through batch ordering or generic release titles. The supplied November 12 edition and production delivery acknowledgements are documented in the included audit.

This repairs full-feed-body extraction and bounded linked-article/model-card hydration; preserves query filters and timestamp provenance; verifies individual AINews discoveries; fixes release filtering, HTML ordering and title collisions; and compares qualifying events globally before caps and publisher diversity. It adds explicit candidate decisions/health diagnostics, bounded catch-up windows with displayed dates, six verified source streams, and schedule updates that preserve other reports' enablement. The duplicate Latent Space feed alias is archived. Existing X budgets, independent runtime boundaries and delivery history are preserved.

Validation:
- Full repository quality gate: 100 tests, Ruff lint/format, source/report validation, generated workflow checks, sdist and wheel builds. Local macOS needed `PYTHONPATH=src` because its editable-install `.pth` is hidden; CI uses a clean install.
- Bounded public HTTP collection/hydration checks against existing and new publishers; evidence included. No paid model/X request or Telegram message was made.
- Regression coverage includes multipart delivery/history and missing model decisions, not just source parsing.

Operational impact: one extra cheap-model consolidation request when multiple stories qualify, plus larger evidence/catch-up inputs. Article fetching is bounded. This PR does not deploy the VPS. Continuous ingestion, TLDR archive integration and operator push alerts remain documented follow-ups.

<a name="pr-2"></a>

## PR 2: feat(sources): add r/singularity and tech-press digests; expand X watchlist to seven

Author: `stefanrossmeier`. Opened: 2026-11-16T20:03:17Z. Merged: 2026-11-16T20:03:26Z.

Sanitized merge: [87feaa24c968](https://github.com/stefanrossmeier/ai-dash/commit/87feaa24c968fc5b03a0c5c921f82366249b6bbb).

### Original description

## What
- **Reddit fixed**: retrieval now sends a full browser User-Agent for reddit.com — Reddit 403s the previous plain `Mozilla/5.0` from datacenter IPs (root cause of the empty community coverage; verified live: 403 → 200)
- **r/singularity** added as a source + dedicated **singularity report**, 2×/day (08:30 / 18:30), Luna ranking, min_score 55, memes/discussion-threads excluded by prompt
- **New tech-press sources** (verified live, all HTTP 200): TechCrunch AI, The Verge AI, MIT Technology Review AI, Ars Technica AI — as a new `News` category + dedicated **ai_news report**, 2×/day (09:15 / 19:15), Luna ranking
- **X watchlist expanded 3 → 7 accounts**: Karpathy, Artificial Analysis, OpenAI, Anthropic, Google DeepMind, Qwen, DeepSeek lab accounts — the best-7 for top AI news (frontier model releases land on these first). Lifted the 3-account caps in `reports.py`/`retrieval.py`; the daily-budget layer already allowed seven
- `research_oss` excludes r/singularity so all six reports stay source-disjoint
- Windmill flow/schedule definitions regenerated from the new config

## Why
The 16 Nov X report said "no qualifying stories": it effectively had one live source and a 60 threshold. Reddit was dead in production (403), and real AI news (e.g. a new Qwen release) surfaces on r/singularity and the tech press the same day.

## Verification
- `./scripts/check.sh` full gates: 113 tests passed, render-windmill check clean, `ai-dash validate` clean
- Live collection verified: r/singularity → 25 items / 22 fresh; ai_news → all 4 sources ok with today's real articles
- Ranking stays on `openai/gpt-6-luna` (rank-cheap alias) per the gpt-5.4-nano deprecation migration

<a name="pr-3"></a>

## PR 3: feat(x): watchlist of seven individual voices; lab news via blog sources

Author: `stefanrossmeier`. Opened: 2026-11-16T20:08:49Z. Merged: 2026-11-16T20:08:56Z.

Sanitized merge: [28d569bc4821](https://github.com/stefanrossmeier/ai-dash/commit/28d569bc4821f88dc67a35376d4f237dc728207c).

### Original description

## What
- **X watchlist → people, not labs.** The five lab accounts (OpenAI, Anthropic, DeepMind, Qwen, DeepSeek) and the Artificial Analysis org account are disabled; the watchlist is now seven influential, active individuals: **Karpathy** (LLM engineering), **swyx** (AI ecosystem news), **Nathan Lambert** (frontier lab developments), **Simon Willison** (LLM tools/apps), **Sebastian Raschka** (research), **Maxime Labonne** (open model releases), **Georgi Gerganov** (local inference). Still exactly 7 (the paid daily-retrieval cap).
- **Lab news via blogs:** added `lab-qwen-blog-rss` (official Qwen blog RSS, verified live: 25 items) to the Lab category → `company` report (07:30/17:30). OpenAI/Anthropic/DeepMind/Mistral/xAI lab blogs were already there; DeepSeek lab releases are covered by the `model-hub-deepseek` HF feed.
- `x_major` report title/focus updated to the people scope; schedules unchanged (20:30).

## Verification
- `./scripts/check.sh`: 113 tests passed, render-windmill clean, `ai-dash validate` clean
- Live collect: Qwen blog + all Lab blog sources fetch (xai-news endpoint remains unavailable as before — pre-existing, unrelated)
- X collection with the new watchlist cannot be live-tested today by design: the daily paid-retrieval budget was consumed by this morning's 20:30 run (old watchlist); the first new-watchlist retrieval fires at tomorrow's 20:30 schedule

<a name="pr-4"></a>

## PR 4: fix(x): single combined retrieval request; per-report gates for posts

Author: `stefanrossmeier`. Opened: 2026-11-17T19:45:10Z. Merged: 2026-11-17T19:45:16Z.

Sanitized merge: [8da2133ce38d](https://github.com/stefanrossmeier/ai-dash/commit/8da2133ce38d3805f3d2d6a048e9186156dd5f3e).

### Original description

## Root causes of the empty 17 Nov X report
1. **Batching vs budget contradiction (real bug):** retrieval split 7 accounts into batches of 3, but the daily budget allows exactly ONE paid X request/day for the whole watchlist → batch 1 consumed the day, the other 4 accounts always failed with RuntimeError. Today's paid response searched only 3 of 7 accounts.
2. **Self-censoring retrieval:** the prompt asked for 'at most two high-signal posts per account' — the model pre-filtered already-paid-for results.
3. **Blog-calibrated gates:** hardcoded `tier >= 3` + min_impact 60 / breadth 45 / novelty 40 / quality 60 meant individual posts could never pass — the Qwen 4 Max post (today's biggest news, retrieved successfully) scored 27.8 against min_score 60 and failed EVERY dimension gate.

## Fix
- `retrieve_x` is now ONE combined request (all handles in a single from:a OR from:b query — verified in today's provider response that one query handles multiple accounts). `x_batch_size` removed. Cost unchanged: ~$0.06/day.
- Retrieval prompt returns all posts up to the schema cap; `max_per_source` 2→3, `max_stories` 6→12.
- Rejection gates (`min_score`, `min_impact`, `min_breadth`, `min_novelty`, `min_quality`, `min_tier`) are now per-report. x_major: score 25, tier 1, impact/breadth/novelty/quality 20/15/10/20 — calibrated against the actual scorer outputs from real posts (the Qwen post now passes).

## Verification
- 113 tests pass; verified against the real 17 Nov selection log that the previously rejected Qwen 4 Max post now clears all gates
- Live end-to-end test (fresh retrieval + Telegram delivery) performed after deploy

<a name="pr-5"></a>

## PR 5: feat(x): replace one-shot daily attempt with a 0.60 USD cost budget

Author: `stefanrossmeier`. Opened: 2026-11-17T19:48:37Z. Merged: 2026-11-17T19:48:41Z.

Sanitized merge: [2879a7625eff](https://github.com/stefanrossmeier/ai-dash/commit/2879a7625eff4deb5046d5e9aa7eac167475a4fc).

### Original description

Replaces the one-paid-request-per-day budget with a **daily cost cap of $0.60** (owner-approved). Each paid request records its actual provider cost; requests are admitted while the day's spend is under the cap; cached responses stay free. A typical watchlist request costs ~$0.06, so the cap allows the scheduled run plus retries/tests. Also removes the different-watchlist refusal (no longer needed — the cost cap and the 7-account limit are the guards).

Failure semantics improve: a transport error or validation failure costs $0, so a bad gateway no longer burns the day's X news.

## Verification
- 113 tests pass, including updated budget/gateway tests for the new semantics (multiple requests under the cap, refusal at the cap, new-day reset, uncached-request retry after transport error)
- Live end-to-end test after deploy

<a name="pr-6"></a>

## PR 6: fix(pipeline): let --example bypass the x_major daily-delivery guard

Author: `stefanrossmeier`. Opened: 2026-11-17T19:50:22Z. Merged: 2026-11-17T19:50:27Z.

Sanitized merge: [12cfeff5953e](https://github.com/stefanrossmeier/ai-dash/commit/12cfeff5953e3955c2357655a6eb56e661b94bcb).

### Original description

The `--example` flag exists to send a labelled test edition, but the daily-delivery guard fired first (`already delivered today`), making same-day verification of report changes impossible. Example runs now bypass the guard; production editions keep it.

<a name="pr-7"></a>

## PR 7: fix(x): store the cost ledger in its own table

Author: `stefanrossmeier`. Opened: 2026-11-17T19:51:45Z. Merged: 2026-11-17T19:51:49Z.

Sanitized merge: [d478d2f0ebd2](https://github.com/stefanrossmeier/ai-dash/commit/d478d2f0ebd2a1cf056b3d1e9f89db8d696828c2).

### Original description

The live container's requests.sqlite still had the legacy schema with day as PRIMARY KEY; sqlite cannot drop a PRIMARY KEY, so the in-place migration failed with a UNIQUE constraint on the first real run. The cost ledger now lives in its own `x_requests` table; the legacy `requests` table is abandoned where present. Caught during live end-to-end verification.

<a name="pr-8"></a>

## PR 8: fix(x): allow seven handles in the gateway request model

Author: `stefanrossmeier`. Opened: 2026-11-17T19:53:30Z. Merged: 2026-11-17T19:53:35Z.

Sanitized merge: [884a6017b950](https://github.com/stefanrossmeier/ai-dash/commit/884a6017b9502d96d7ef8e9863505850350de7fb).

### Original description

`SearchRequest.allowed_x_handles` still had `max_length=3` from the batched-retrieval era. The single combined watchlist request sends all seven handles and was rejected with 422 by request validation — before the configured-watchlist check even ran. Aligned with the seven-account watchlist limit (the same cap enforced by `x_budget` and `retrieve_x`).

Caught during live end-to-end verification of the X report fix.

<a name="pr-9"></a>

## PR 9: feat(x): optimize watchlist for high-frequency AI news spreaders

Author: `stefanrossmeier`. Opened: 2026-11-17T20:02:38Z. Merged: 2026-11-17T20:02:43Z.

Sanitized merge: [bb32fb03082e](https://github.com/stefanrossmeier/ai-dash/commit/bb32fb03082e8bb78c77f8e72429e83e5b29eccf).

### Original description

## What
Replaces the four lowest-frequency X voices (Karpathy, Raschka, Gerganov, Labonne — days between posts) with four of the highest-frequency AI news spreaders on X:

- **\@akhaliq** — among the fastest same-day AI research/model-release news accounts
- **\@reach_vb** — HF community voice; open-model releases within minutes
- **\@minchoi** — high-volume papers/product news
- **\@TheAIGRID** — high-volume general AI news

swyx, Nathan Lambert and Simon Willison stay (they produced all of the 17 Nov report's items). The report focus is updated: the bucket surfaces the day's AI developments at volume; ranking selects the most important.

## Why
The report's value is 'up to date without scrolling' — the input bucket must be accounts that actually post daily news. Dropped accounts stay configured-but-disabled for future re-addition.

## Verification
- `./scripts/check.sh`: 113 tests passed; render-windmill clean; validate clean
- Live retrieval test with the new watchlist after deploy

<a name="pr-10"></a>

## PR 10: feat(x): ten high-frequency news accounts; drop history omission

Author: `stefanrossmeier`. Opened: 2026-11-17T20:15:35Z. Merged: 2026-11-17T20:15:41Z.

Sanitized merge: [720f4419b077](https://github.com/stefanrossmeier/ai-dash/commit/720f4419b077dda84d24dc53f2fe592386cc4637).

### Original description

## What
- **Watchlist 7 → 10 accounts** with three more known high-value, high-frequency AI news posters: \@ClementDelangue (HF co-founder — open-model news), \@AndrewYNg (The Batch — industry news), \@rowancheung (The Rundown — breaking AI news/launches). Account cap raised from 7 to 10 in all four enforcement points (budget, retrieval, gateway model, report selection); the $0.60/day cost budget still bounds spend.
- **History omission removed for x_major** (`omit_delivered: false`): the grok retrieval is the expensive part, Telegram posting is free — a still-relevant story should appear regardless of whether yesterday's edition carried it. Within-run dedup remains; other reports keep the default.

## Verification
- `./scripts/check.sh`: 113 tests pass (disjointness updated to the 10-account set, cap tests use 11 handles, empty-message text updated)
- Live full report after deploy with a fresh paid retrieval

<a name="pr-11"></a>

## PR 11: feat(x): score decides on routine-labelled items for the X report

Author: `stefanrossmeier`. Opened: 2026-11-17T20:22:48Z. Merged: 2026-11-17T20:22:52Z.

Sanitized merge: [fe2608ddce4e](https://github.com/stefanrossmeier/ai-dash/commit/fe2608ddce4e07ef43c8f3ff17bb2762973edd61).

### Original description

Diagnosis of the thin 17 Nov edition (6 retrieved, 3 delivered): the two omissions were a 24.8-score personal-project ship (fine to omit) and 'Claude can now fold your iPhone' — score **38.3, above every threshold**, hard-rejected only because the scorer labelled it `routine_update`. For a potpourri report that gate is miscalibrated; the composite score already penalizes routine items.

`reject_routine_updates` is now a per-report setting (default on, so company/blogs/etc. are unchanged); `x_major` sets it false and relies on the score threshold. Verified against the real 17 Nov selection log: the Claude item now passes, the Datasette item (24.8 < 25) still does not.

113 tests pass.

<a name="pr-12"></a>

## PR 12: feat(x): extend watchlist to fourteen high-frequency news accounts

Author: `stefanrossmeier`. Opened: 2026-11-17T20:29:39Z. Merged: 2026-11-17T20:29:43Z.

Sanitized merge: [abd61009e734](https://github.com/stefanrossmeier/ai-dash/commit/abd61009e73457d3eca69dfa481a7456f35516a2).

### Original description

Adds four more high-value, high-frequency AI news posters from the owner's researched list: \@heyBarsee, \@kimmonismus (Chubby), \@BinduReddy, \@LinusEkenstam. Watchlist is now 14 accounts (cap raised 10→14 in all four enforcement points). Retrieval stays a single combined grok query per day, so cost per edition is unchanged (~$0.06-0.07).

Existing accounts stay: swyx, Lambert, Willison, akhaliq, reach_vb, minchoi, TheAIGRID, Delangue, Ng, Cheung.

## Verification
- `./scripts/check.sh`: 113 tests pass (disjointness at 14 accounts, cap tests at 15 handles, 118 sources)
- Live full report with the 14-account watchlist after deploy

<a name="pr-13"></a>

## PR 13: feat(x): batch retrieval for search recall; per-handle-set cache

Author: `stefanrossmeier`. Opened: 2026-11-17T20:32:31Z. Merged: 2026-11-17T20:32:36Z.

Sanitized merge: [9e4b93febf4e](https://github.com/stefanrossmeier/ai-dash/commit/9e4b93febf4e94bad3d88659631bbcc0f92e3008).

### Original description

Live evidence from today's runs: the 14-handle single query returned 2 items while 10- and 7-handle queries on the same day returned 6 and 3 — grok's X search loses recall as one OR-query widens.

- `retrieve_x` batches accounts in chunks of ≤5 (3 paid requests for 14 accounts ≈ $0.20/day, well under the $0.60 cost budget)
- The gateway day-cache (built for the one-request-per-day era) becomes a **per-handle-set cache**, so batches don't collide and identical batches stay free

113 tests pass.

<a name="pr-14"></a>

## PR 14: feat(x): one bounded retry per retrieval batch

Author: `stefanrossmeier`. Opened: 2026-11-17T20:36:17Z. Merged: 2026-11-17T20:36:22Z.

Sanitized merge: [7137537e5543](https://github.com/stefanrossmeier/ai-dash/commit/7137537e55436e6098695922456120598254e5ad).

### Original description

Live finding: the 17 Nov batch (BinduReddy, LinusEkenstam, akhaliq, reach_vb, minchoi) failed because grok returned one post without citation evidence — strict anti-hallucination validation (kept) dropped all five accounts.

Each ≤5-account batch now gets exactly one retry before giving up; the $0.60/day cost budget bounds the extra spend (~$0.12/batch worst case). The gateway also records provider cost on failed validation calls, so the ledger no longer undercounts actual spend. Updated the two no-retry-era tests to the bounded-retry contract.

113 tests pass.

<a name="pr-15"></a>

## PR 15: fix(x): drop only violating posts in citation validation

Author: `stefanrossmeier`. Opened: 2026-11-17T20:42:02Z. Merged: 2026-11-17T20:42:07Z.

Sanitized merge: [fed575066aba](https://github.com/stefanrossmeier/ai-dash/commit/fed575066aba069d378415ab862809a48b27a03d).

### Original description

One uncited provider post currently fails its whole ≤5-account batch — on 17 Nov that twice blacked out BinduReddy, LinusEkenstam, akhaliq, reach_vb and minchoi for the day, which is exactly where the GPT-6.2 Astra release news came from.

- Per-post violations (no citation, out-of-scope author, malformed URL, over the per-author limit) now **drop only that post**, recorded as `dropped_posts` in the audit; nothing uncited ever reaches the pipeline
- Structural violations (incomplete body, search-count/tool contract, query scope/date) still fail the whole response — those indicate systemic provider misbehavior
- Fixed two latent cap mismatches: `Posts` max 6→15 (matches the retrieval schema's 3/account × 5 accounts) and the per-author limit 2→3 (matches `max_per_source: 3`)

113 tests pass; unsafe-response tests split into structural (still raise) and per-post (drop) contracts.

<a name="pr-16"></a>

## PR 16: fix(x): soften breadth and quality gates for short X posts

Author: `stefanrossmeier`. Opened: 2026-11-19T19:49:14Z. Merged: 2026-11-19T19:49:18Z.

Sanitized merge: [b20563a5991d](https://github.com/stefanrossmeier/ai-dash/commit/b20563a5991d231e42c1cb706336570ddf221a78).

### Original description

The 19 Nov 20:30 edition was empty although retrieval delivered 9 items and two scored above threshold:

- Gemini Neon **#1 on LiveBench** (score 25.7) — rejected `weak_evidence`: quality 15 < 20. A tweet never carries methodology.
- Frontier-convergence analysis (score 27.4) — rejected `weak_evidence`: quality 12 < 20.

The quality/breadth gates were calibrated for blog posts; X posts systematically score 10–25 on them. `min_breadth` 15→10, `min_quality` 20→10 **for x_major only** — score, impact, novelty and tier unchanged; other reports keep strict gates.

Re-simulated tonight's six ranked items against the new gates: 2 stories would have been delivered instead of 0. 113 tests pass.

<a name="pr-17"></a>

## PR 17: feat(x): free Nitter RSS timelines, X-calibrated potpourri ranking

Author: `stefanrossmeier`. Opened: 2026-11-19T19:57:30Z. Merged: 2026-11-19T19:57:36Z.

Sanitized merge: [4dc240b0ce04](https://github.com/stefanrossmeier/ai-dash/commit/4dc240b0ce049cd0a6ab997dd9a6eebf98b09807).

### Original description

Rework of the daily X report after two empty editions in three days (9 items retrieved, 0 delivered both times):

**Wrong assumption 1 — sampled retrieval.** grok search returned ≤3 posts/account and `max_per_source: 3` truncated even those. Real volume never reached ranking.

**Wrong assumption 2 — blog-calibrated ranking.** The quality gate demanded in-post methodology and rejected real news from short posts; breadth rejected anything without a broad write-up.

**Changes**
- `retrieve_x` serves **full per-account timelines via free Nitter RSS** (live-verified 2026-11-19: 13/14 handles, 20–25 fresh posts each). **Paid grok retrieval is parked out of the normal runs** — daily X cost drops to $0 and no paid path can silently starve the report. Per-handle failure isolation instead of whole-batch loss.
- `max_per_source` 3→25 for x_major.
- New `assets/x-editorial.md`: potpourri ranking — exclude only crap (memes, hype, reposts, personal minutiae), keep tier-2 concrete news, X-specific calibration (never demand methodology in a tweet; breadth/impact judged from the claim). Selectable per report via the new `ranking_prompt` setting.
- Paid-path code (`_retrieve_x_batch`, `X_POST`) removed; recoverable from git history when a paid report is wanted.

111 tests pass (RSS contract: timeline parsing → canonical status URLs, no-paid-path assertion, per-handle isolation).

<a name="pr-18"></a>

## PR 18: fix(x): consolidation retries once and falls back instead of aborting

Author: `stefanrossmeier`. Opened: 2026-11-19T19:59:55Z. Merged: 2026-11-19T20:00:00Z.

Sanitized merge: [65ad6fb2b6c7](https://github.com/stefanrossmeier/ai-dash/commit/65ad6fb2b6c723ffacfc9e5172a34bdfa9086cde).

### Original description

The first full-timeline potpourri run aborted with `consolidation must account for every candidate exactly once` — at RSS volumes the grouping model returned IDs inexactly and the exactness check killed the whole edition.

Consolidation is now fail-safe: one bounded retry → audit entry → **fallback to ungrouped stories** (delivery continues). The system prompt also names the exact ID count. Test updated to the new contract.

111 tests pass.

<a name="pr-19"></a>

## PR 19: feat(x): three free daily potpourri editions at 07:45, 11:45, 19:45

Author: `stefanrossmeier`. Opened: 2026-11-19T20:08:30Z. Merged: 2026-11-19T20:08:35Z.

Sanitized merge: [727d69413917](https://github.com/stefanrossmeier/ai-dash/commit/727d694139178ffa750a4e04242fd414e483396b).

### Original description

With free Nitter RSS retrieval each edition costs $0, so the X report moves from one slot (20:30) to three: **07:45, 11:45, 19:45** — all free slots, no overlap with company (07:30), singularity (08:30/18:30), ai_news (09:15/19:15) or blogs (12:30).

- `x_major` slots: `20:30` → `07:45`, `11:45`, `19:45`
- The one-daily-slot validator loosened to a non-empty check
- Windmill schedules re-rendered (3 files)

111 tests pass.

<a name="pr-20"></a>

## PR 20: fix(x): remove once-per-day guard blocking the 11:45 and 19:45 slots

Author: `stefanrossmeier`. Opened: 2026-11-20T07:32:31Z. Merged: 2026-11-20T07:32:34Z.

Sanitized merge: [01c45dea0f38](https://github.com/stefanrossmeier/ai-dash/commit/01c45dea0f38c6359ece82934bf160f25a476cb6).

### Original description

The 07:45 schedule fired today but skipped: `delivered_report_today` saw a manual 06:53 run and returned `already delivered today`. That guard is a single-slot-era leftover — with three slots it would permanently silence the 11:45 and 19:45 editions.

- Guard (and its now-dead storage helper) removed
- `omit_delivered: true` for x_major: each edition delivers only stories not already sent today, so the 11:45/19:45 editions carry the posts made since morning instead of repeating

111 tests pass.

<a name="pr-21"></a>

## PR 21: fix(x): deliver every slot in full; repetition is accepted by design

Author: `stefanrossmeier`. Opened: 2026-11-20T07:33:03Z. Merged: 2026-11-20T07:33:07Z.

Sanitized merge: [f6919a668653](https://github.com/stefanrossmeier/ai-dash/commit/f6919a6686533f00c115422fe554246f37cd3587).

### Original description

Per owner direction: no edition is ever skipped or thinned. `omit_delivered` stays **off** for x_major — each of the three daily slots delivers the full 24h potpourri, duplicates across the day included.

<a name="pr-22"></a>

## PR 22: feat(gateway): rank through the dedicated llm-gateway instance

Author: `stefanrossmeier`. Opened: 2026-11-21T10:24:51Z. Merged: 2026-11-21T10:24:56Z.

Sanitized merge: [8aae49e5937e](https://github.com/stefanrossmeier/ai-dash/commit/8aae49e5937e18b8cbd21f78ba2c0f1043f38338).

### Original description

Ranks move from the old borrowed model gateway to **ai-dash's own llm-gateway instance** (per-project config/secrets/token/ledger; image pinned at `1dfc543`).

- `Gateway` client: Bearer auth from a private token file (`AI_DASH_GATEWAY_TOKEN_FILE`) + `Idempotency-Key` per request — retries recover the same logical request
- All three ranking payloads already match the frozen `DashboardChat` wire (`purpose`, `profile`, `response_schema`)
- X retrieval unchanged: free Nitter RSS + the bounded x-gateway
- Compose: `AI_DASH_GATEWAY_URL → http://ai-dash-llm-gateway:8080` (instance joined to the project network), token mounted read-only

110 tests pass. Live smoke after deploy: a real edition through the instance.

<a name="pr-23"></a>

## PR 23: feat(scripts): deterministic post-deployment smoke test

Author: `stefanrossmeier`. Opened: 2026-11-21T13:43:13Z. Merged: 2026-11-21T13:43:17Z.

Sanitized merge: [6f0b28907093](https://github.com/stefanrossmeier/ai-dash/commit/6f0b28907093084fe5205e79c3b0b1210aabbd2b).

### Original description

13 deterministic post-deploy checks for the ai-dash stack, mirroring daily-dash's `scripts/smoke-test.sh` where applicable but reflecting this stack's own shape:

- Full stack: db, Windmill server/worker, bounded x-gateway, legacy model gateway **and the dedicated llm-gateway instance** (container + `/ready` + principal `project_id: ai-dash`)
- Schedules via host-side Windmill API (runtime profile token, like `register-windmill.py`) — all rendered schedules present and enabled
- Worker reads `/data/ai-dash/state.sqlite` — no git check, this project persists SQLite + artifacts, not a git data repo
- Worker log scanned for infrastructure failures since container start (empty-window transients excluded as WARN)

Live result: 13 PASS / 1 FAIL (dirty checkout = this new script itself). Also removed the obsolete disabled `f/ai_dash/x_major_2030` schedule left on the Windmill server from the three-slot migration.

<a name="pr-24"></a>

## PR 24: fix(windmill): run_digest exports the llm-gateway instance and token

Author: `stefanrossmeier`. Opened: 2026-11-21T17:20:14Z. Merged: 2026-11-21T17:20:19Z.

Sanitized merge: [4b2ef5ceb7d8](https://github.com/stefanrossmeier/ai-dash/commit/4b2ef5ceb7d88aad991437cdcfdf5202ed6bc32a).

### Original description

Same bug class as daily-dash PR #17, found by auditing the old gateway's logs after the migration: **scheduled** ai-dash flows still ranked via the old model gateway — Windmill jobs run a sanitized env, so the worker's `AI_DASH_GATEWAY_URL` never reaches the job and `run_digest.sh`'s old default applied. Today's 11:45 x_major, 12:30 blogs and 15:30 research_oss all POSTed there (manual docker-exec runs carried the env and masked it).

`run_digest.sh` now defaults to `http://ai-dash-llm-gateway:8080` and exports `AI_DASH_GATEWAY_TOKEN_FILE`.

<a name="pr-25"></a>

## PR 25: fix(gateway): stable idempotency key and data-availability smoke classification

Author: `stefanrossmeier`. Opened: 2026-11-21T18:03:55Z. Merged: 2026-11-21T18:04:12Z.

Sanitized merge: [c612c336b1cc](https://github.com/stefanrossmeier/ai-dash/commit/c612c336b1cc6ab6afc792843a5eb53bfe2add14).

### Original description

## What
1. **Idempotency key** (`src/ai_dash/gateway.py`): was `ai-dash:<uuid4()>` per call — a retry became a new paid request despite the "retries stay idempotent" comment. Now derived from the canonical request body, so retries replay the recorded result.
2. **Smoke classification** (`scripts/smoke-test.sh`): `no source produced dated items` (a slot legitimately refusing an empty/undated edition) was counted as an infrastructure failure, failing the gate on a healthy stack. It is now grouped with `no qualifying` as a data-availability warning.

## Verification
- `pytest`: 112 passed (new tests pin stable/unique keys and that X search stays on ai-dash's own gateway without auth headers).
- Live stack: the smoke test went from 13/14 to 14/14 after the classifier fix.

## Rollback
Revert; per-call random keys and the stricter classifier return.

<a name="pr-26"></a>

## PR 26: fix(gateway): scope the idempotency key to one run

Author: `stefanrossmeier`. Opened: 2026-11-21T18:28:23Z. Merged: 2026-11-21T18:28:34Z.

Sanitized merge: [1802e8159d5c](https://github.com/stefanrossmeier/ai-dash/commit/1802e8159d5c532d1c0981c996affd88bbe23611).

### Original description

## What
Follow-up to #25. A content-only key makes an identical request permanent: a failed request could never be rerun, and the next scheduled edition would replay the terminal failure instead of executing.

The key is now `ai-dash:<run-nonce>:<content-sha256>` — the nonce is generated once per process (one Windmill job run), so retries inside a run still replay the recorded result while a new run executes as a new request.

## Verification
- `pytest`: 112 passed; the test pins all three cases (same run stable, changed body distinct, new run distinct).

## Rollback
Revert; content-only keys return.

<a name="pr-27"></a>

## PR 27: style(tests): apply ruff format to the gateway client test

Author: `stefanrossmeier`. Opened: 2026-11-21T18:29:21Z. Merged: 2026-11-21T18:29:25Z.

Sanitized merge: [2b043d297ccc](https://github.com/stefanrossmeier/ai-dash/commit/2b043d297ccc37addd93690d2df66178b8566e5e).

### Original description

Follow-up to #25/#26: the new test file was not ruff-formatted, so `scripts/check.sh` failed at the format gate on main. Formatting only.

Verification: `./scripts/check.sh` passes end to end (ruff check, ruff format, 112 tests, config validation, wheel build).

<a name="pr-28"></a>

## PR 28: feat(youtube): add rolling daily YouTube report

Author: `stefanrossmeier`. Opened: 2026-11-25T12:10:40Z. Merged: 2026-11-25T12:22:21Z.

Sanitized merge: [1c918bf8155b](https://github.com/stefanrossmeier/ai-dash/commit/1c918bf8155bd3bf40f64f851af883f1062af561).

### Original description

## What and why

Adds a daily YouTube new-upload report at 19:30 Europe/Berlin. It retrieves each channel's public Atom feed by its configured channel ID, keeps Shorts, converts links to canonical `watch?v=` URLs, and shows each title, channel name, publication time, and URL.

The five channels are defined in `config/youtube_channels.yaml` with stable IDs, display names, handles, validated channel IDs, and enabled flags. The file is loaded on every collection relative to `AI_DASH_HOME`; channel edits therefore require no code change. Each channel gets separate `ok`, `empty`, `unavailable`, or `disabled` coverage. The configured handle `@jamwithai` has the RSS display/feed title `Jam With AI | Shirin Khosravi Jam`.

The `no_llm` report override bypasses both `hydrate()` and `rank()`. It selects the rolling `now - 24h .. now` window deterministically, newest first, capped at `max_stories`, with no ranking traces or gateway calls. Rendering omits the summary line.

## Verification

- `./scripts/check.sh`: passed; Ruff, 90 pytest tests, `ai-dash validate` (119 sources, 7 reports), Windmill `--check`, and `uv build` all succeeded.
- Live `uv run ai-dash collect --report youtube`: AI Engineer `ok` (2 items, 2 fresh); Julian Ivanov `empty` (0); The AI Automators `empty` (0); Jam With AI `empty` (0); Matt Pocock `empty` (0). The four empty feeds were reachable but had no uploads inside this run's 24-hour window. `traces: []`.
- Focused tests: `test_youtube_feed_parses_fixture_and_canonicalizes_shorts`, `test_youtube_feed_excludes_entries_older_than_24_hours`, `test_youtube_channel_ids_are_validated`, `test_youtube_channel_failures_are_isolated_and_reported`, and `test_no_llm_build_uses_rolling_window_without_gateway_calls`.

The live run did not produce fresh items from all five channels as requested; only AI Engineer had fresh uploads. Empty statuses are reported as observed, not treated as channel failures.

## Deployment

The generated `youtube_1930.schedule.yaml` remains disabled. At deploy time, register it with `scripts/register-windmill.py --enable-report youtube`. No schedule was registered and nothing was deployed for this PR.

<a name="pr-29"></a>

## PR 29: Use fresh cadence windows and constrain public source fetching

Author: `stefanrossmeier`. Opened: 2026-11-25T15:54:02Z. Merged: 2026-11-25T15:54:42Z.

Sanitized merge: [7e7a3d04b01f](https://github.com/stefanrossmeier/ai-dash/commit/7e7a3d04b01f9421b1336a4060999d56ba080581).

### Original description

Reports now retrieve the preceding scheduled interval plus a small overlap, including uneven schedules and daylight-saving changes. Failed unsent editions remain in the audit trail and are discarded so recovery retrieves fresh news. Oversized ranking and summary inputs split only after explicit safe input-limit rejection, preserving every candidate and stable request identity. Includes the project-owned Reddit OAuth recovery and preserves the YouTube report.

Public feeds, HTML, article hydration, YouTube and Nitter use address-checked HTTP connections pinned to validated public IPs, with the original Host and TLS identity. Every redirect is checked; responses have streaming byte limits and reject compression before decoding. Authenticated Reddit, gateway and Telegram clients retain their separate fixed-service boundaries.

Validation: complete scripts/check.sh gate passed with 128 offline tests, Ruff lint/format, configuration validation, generated Windmill checks, source distribution and wheel builds. Gitleaks found no credentials in current source or all locally available branch/reflog history. Free live checks fetched OpenAI RSS, YouTube and Nitter successfully through the hardened transport. No manual model inference or Telegram messages were used for verification.

<a name="pr-30"></a>

## PR 30: Repair singularity community ranking and document secure operation

Author: `stefanrossmeier`. Opened: 2026-11-25T16:12:28Z. Merged: 2026-11-25T16:16:45Z.

Sanitized merge: [b223bcddf843](https://github.com/stefanrossmeier/ai-dash/commit/b223bcddf84311ee6663a3c8aaf2a2aaee0f0dce).

### Original description

The singularity collector recovered but its latest successful run rejected all 18 posts and sent nothing. Fourteen evidence requests targeted blocked Reddit discussion pages, while the shared blog policy required independently established high-impact results. A dedicated community prompt/gates now admits substantive discussions and attributed reported claims, retains crosspost context, and hydrates primary links without changing Reddit identity or submission dates. Summaries must preserve uncertainty rather than presenting purported proofs or rumors as facts.

Adds the full portfolio/privacy review and current architecture, interface and operations docs; removes unnecessary operator identifiers from current docs while explicitly retaining history; corrects stale gateway/source guidance; and adds a checksum-verified Gitleaks history/checkout job with broader private-file excludes. Smoke readiness checks the token inside the worker and includes the orchestration worker. The local quality gate reinstalls the current noneditable package and avoids implicit environment resynchronization.

Validation: 137 offline tests, Ruff, configuration and generated-workflow checks, source/wheel builds, shell syntax, documentation links and redacted secret scans passed. Current PyPI advisory audit found no known vulnerability in 33 third-party distributions; the local project was skipped. No manual Telegram send or paid example run is included in this validation; the requested labeled example follows deployment.

<a name="pr-31"></a>

## PR 31: Prepare clean source publication candidate and record release gates

Author: `stefanrossmeier`. Opened: 2026-11-25T16:40:00Z. Merged: 2026-11-25T16:47:03Z.

Sanitized merge: [852e78ccfcc5](https://github.com/stefanrossmeier/ai-dash/commit/852e78ccfcc5b50fd721852575f78c8f6adc8ef9).

### Original description

The operational repository is not suitable for a simple visibility flip without a privacy decision: old Git and retained CI logs still contain operator details. A committed-path source exporter now produces a deterministic, secret-scanned candidate without Git history, private audit dossiers or raw production snapshots. It rejects links/private paths and refuses archive or receipt overwrites. The key-free quickstart and synthetic example are runnable from that export.

Adds scoped security/contribution guidance, Apache-2.0 wheel metadata and third-party notices, freezes Hatchling and pins CI actions to verified commit revisions. Current source documentation now distinguishes source publication from the unresolved Windmill CE image terms and inherited runtime advisory backlog. The normal source-distribution build now excludes operational dossiers, and the quality gate inspects actual source/wheel members against the publication manifest. The gate failed on the old artifact containing AGENTS.md and passes after the fix. No application behavior, source policy, deployed container or repository visibility is changed.

Validation: 141 tests, lint/format/config/generated workflow checks and source/wheel builds passed both in the checkout and from the clean 104-file export. The candidate passed redacted Gitleaks and local-link checks; wheel metadata includes the application license and notices. All 104 retained CI runs (296 logs) and all 30 PR discussions/reviews were inspected, with no credential found in those published-content surfaces. The read-only exact-image scan and its limitations are documented; no broad vulnerability suppression or container approval was added.

<a name="pr-32"></a>

## PR 32: Correct disclosure classification and preserve portfolio history

Author: `stefanrossmeier`. Opened: 2026-11-25T16:57:15Z. Merged: 2026-11-25T16:59:15Z.

Sanitized merge: [0f0059f11153](https://github.com/stefanrossmeier/ai-dash/commit/0f0059f11153f003b26af963b56db3dd57a5d67f).

### Original description

Corrects the initial disclosure inventory after manual line-context review: CI operator-name matches were branch refs, and alleged home paths were Windmill API routes. These alerts do not justify log deletion. Genuine older documentation metadata remains a selective privacy choice, with no credential finding requiring wholesale history replacement.

Updates the publication assessment to preserve meaningful history for developer/architect review, with explicit examples of what the history demonstrates and which earlier guarantees deserve explanation. No Git rewrite, CI deletion, application change, image release or visibility change is included. Documentation-only; local diff checks passed. Existing runtime/source checks remain unchanged.

<a name="pr-33"></a>

## PR 33: Clarify AI Dash outcomes, preserve engineering history and refresh archdoc

Author: `stefanrossmeier`. Opened: 2026-11-25T17:18:46Z. Merged: 2026-11-25T17:19:53Z.

Sanitized merge: [537ecf599949](https://github.com/stefanrossmeier/ai-dash/commit/537ecf59994910180ce27746c52de8ac3a131e2c).

### Original description

AI Dash could complete a job without qualifying stories, while its status did not show whether the latest edition was quiet or its message parts were acknowledged. Status now separates selection from delivery, including partial and uncertain outcomes, and the smoke check prints those diagnostics separately from infrastructure readiness.

Refresh all four architecture guides using ai-craftkit archdoc with provenance and revision-pinned evidence. Add a concise evolution guide linking historical claims to corrections and current limits; preserve Git/PR/CI history. Add a Safeplane-style text banner and route AGENTS.md to the guides while retaining real contributor authorship. Include that public-safe guidance in source packaging. Copy the license files required by package metadata into the deployment build.

Validation: 151 offline tests; Ruff; configuration/generated-workflow checks; source/wheel publication-path and license checks; shell syntax; 76 revision-pinned source targets; local Markdown targets; redacted worktree Gitleaks scan. No paid inference or Telegram send used.

Remaining limits stay explicit: root worker, inherited runtime image advisories and unresolved upstream derived-image terms. These changes do not establish image redistribution approval or a hardened multi-tenant deployment.

