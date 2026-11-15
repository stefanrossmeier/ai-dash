# Source provenance

## News repair — 2026-11-15

The live registry now retains the original 95 entries plus six verified additions:
Anthropic Engineering, Anthropic Research, Claude Code releases, Codex releases,
THE DECODER and Import AI. The original Latent Space alias is disabled because it
returns exactly the same all-content stream as the canonical Latent Space / AINews
row. Active report counts are 20 company, seven analysis, 24 research/OSS and three X.

Full feed bodies are read before teasers; bounded hydration supplies article/model
card evidence where needed. Source URL query parameters are preserved, including
HF author, ordering and limit filters. Model-hub author endpoints sort by
`lastModified`; GitHub discovery now means recently active repositories, not
“Trending” or newly created projects. Repository updates and paper curation retain
their timestamp basis and never establish a release by themselves.

[Repair verification](NEWS_REPAIR_2026-11-15.md) and the linked evidence record
the free public-source checks. TLDR AI remains a candidate requiring a verified
archive adapter; it was not enabled from a landing page alone. No paid X watchlist
or daily retrieval/delivery limit changed.

The remaining sections describe the original registry and historical rollout.

Imported on 2026-11-09 from the owner's existing Hermes installation, not generated
from a model's recommendations:

1. Local reference repository: `hermes-config`,
   `machines/source-machine/hermes/skills/devops/ai-news-pipeline/SKILL.md`.
2. Endpoint notes in that skill's `references/source-endpoints.md`.
3. The skill names `~/.hermes/ai-news/sources.md` as its authoritative registry.
   That file is not included in the hermes-config checkout. It was read from the
   configured SSH host `source-host` (`~/.hermes/ai-news/sources.md`).
4. An exact snapshot is committed as `docs/hermes-sources.md` (95 rows).

`scripts/import-hermes-sources.py` deterministically converts the snapshot into
`config/sources.yaml`. Blog-to-feed adaptations are the endpoints documented in
the Hermes skill. Other HTML pages are fetched at their ORIGINAL registry URL;
feeds are used only when advertised by the publisher. GitHub releases use Atom,
arXiv uses its official category Atom feeds, Hugging Face uses native JSON APIs, Hacker News uses Algolia,
and GitHub discovery uses repository search. Original source URLs remain alongside
adapter endpoints so discovery adaptations are inspectable.

The four benchmark rows remain in the registry as `manual`: undated leaderboard
changes are not automatically news. Source failure is a measured coverage state.
`ok` requires at least one dated item; `fresh` reports its contribution to the
24-hour window. X coverage means a native search completed, not exhaustive retrieval.
Model IDs and repository creation times are discovery signals, not verified release announcements.

To change sources, edit `config/sources.yaml`. Re-running the importer intentionally
resets that file to the captured registry. Add future sources only with an explicit
provenance note and verify dated item output before claiming coverage.

## Verified endpoint repairs (2026-11-09)

The initial live smoke test found HTTP errors from the arXiv API and smol.ai.
No replacement sources were added. The existing three arXiv rows now use
`https://rss.arxiv.org/atom/cs.CL`, `cs.LG`, and `cs.AI`, following
[arXiv's feed documentation](https://info.arxiv.org/help/rss.html). All three
returned HTTP 200 and dated entries (146, 417 and 397 in the verification run).

The original smol.ai URL resolves to `https://latent.space/news/`. That publisher
advertises `/feeds/all.xml` in its HTML alternate links; the feed returned 20 dated
entries. The original registry URL is preserved, and the endpoint note explains
that this is the publisher's broader feed. Shared stories with the existing
Latent Space row are deduplicated. Baseten's JS-only page and the blocked Reddit
endpoint remain explicit gaps; related X sources remain independent collection paths.

## Source-based rollout and X cost limit

The 95-row registry is preserved. Automatic reports use disjoint source groups
from `config/reports.yaml`. All original X entries are disabled in the base registry;
only seven official lab accounts are explicitly re-enabled by `x_major`. The other
38 X accounts stay archived. Native X search has one persistent daily retrieval
attempt, no paid retries, and cached reuse for previews/manual runs. No report
other than `x_major` contains X sources.

## Overlap crosscheck — 2026-11-09

OpenAI RSS and Anthropic News are configured and were checked from the VPS worker.
OpenAI returned 25 dated entries including two fresh ones. Anthropic initially
returned eight older articles: its latest feature linked outside `/news/`, so the
collector missed it. Dated `<article>` cards are now parsed before path-restricted
fallback discovery, with an explicit publisher date and same-host URL validation.
Regression coverage includes a root-path announcement with a textual `<time>`.

DeepMind, Mistral and xAI also have configured company blogs. Qwen/DeepSeek model
releases are partially covered by model hubs; these do not cover all commentary.
Paid X slots now supplement these sources with three existing Hermes entries:

- Andrej Karpathy (`@karpathy`): independent technical commentary; no dedicated
  automated source for him in the current reports. [Personal site](https://karpathy.ai/).
- François Chollet (`@fchollet`): abstraction/ARC/generalization commentary; no
  dedicated automated source in the current reports. [Personal site](https://fchollet.com/).
- Artificial Analysis (`@ArtificialAnlys`): independent benchmark updates. Its
  registry leaderboards are manual, so they are not automatically collected.
  [About](https://artificialanalysis.ai/about).

This avoids dedicated-source duplication, not every incidental mention in an
aggregator. Existing once-per-day retrieval/delivery guards stay in effect.
No extra X scan is made when changing the watchlist during an already-used day.

After the repair, the deployed Anthropic collector returned seven dated articles,
including two inside the current 24-hour window. OpenAI returned 25 dated entries,
including two fresh ones. The once-daily complementary X configuration was deployed
without clearing today's budget or making another paid request.
