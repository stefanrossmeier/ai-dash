# Source registry and provenance

## Current configuration

`config/sources.yaml`, `config/reports.yaml` and `config/youtube_channels.yaml`
are authoritative. The registry contains 119 entries, including archived and
manual sources. Report membership is 21 company, seven analysis, 24 research/OSS,
fourteen X, one Reddit OAuth listing, four tech-press feeds and one YouTube channel
registry. The latter expands into five enabled channels. These are configuration
counts, not measurements of current source availability.

Reports use cadence-derived windows, with original timestamp basis preserved.
An old paper newly curated today is labeled as curation, a repository push as
activity, and a Reddit post as submission; none alone establishes a new release.

## Adapters and evidence

| Input | Acquisition and limitations |
| --- | --- |
| RSS/Atom | Publisher-declared endpoints, dated entries and full available bodies before teasers |
| HTML | Publisher cards/metadata and advertised feeds, followed by bounded article evidence |
| GitHub | Release Atom feeds or recently active LLM repository discovery; stable releases exclude prerelease markers |
| Hugging Face | Native model/paper APIs, model-card evidence and distinct activity/curation dates |
| Hacker News | Dated AI-related submissions and bounded linked article hydration |
| Reddit | r/singularity uses approved OAuth; preserves submission/crosspost text and hydrates external primary links |
| X | Free Nitter RSS for configured accounts; no paid retrieval fallback or completeness guarantee |
| YouTube | Public upload Atom feeds by validated channel ID; no video/transcript summarization |
| Manual benchmarks | Registry provenance only; undated leaderboard changes are not automatically news |

Collection records ok, empty, unavailable, undated, manual, disabled and
search-required outcomes. A successful adapter request does not mean a delivered
story, exhaustive coverage or independent validation. Quiet editions and failed
sources remain distinct. Public-source fetching validates/pins global addresses,
checks redirects and bounds response bytes; see [deployment](DEPLOYMENT.md).

Native Reddit discussion text comes from OAuth rather than repeated HTML scraping.
When a primary link exists, its evidence can be added without replacing the
Reddit discussion's identity or submission time. Community ranking and summaries
must distinguish reported claims from established facts.

## Provenance and changes

The original 95-row snapshot was captured on 9 November 2026 from the owner's
Hermes news-pipeline registry and endpoint notes. Its public-source rows remain in
[the captured registry](hermes-sources.md). Private host/machine paths are not
required to use or reproduce the application.

Later additions and endpoint adjustments are represented in current configuration
and source notes. The duplicate Latent Space alias is archived rather than counted
as independent coverage. Current X accounts and source-specific reports supersede
the retired paid-X/shared-runtime configuration.

Edit the current configuration for ordinary changes. The historical importer
`scripts/import-hermes-sources.py` reconstructs the original snapshot and overwrites
`config/sources.yaml`; it is not an additive synchronization command. Verify usable
dates and evidence before representing a new endpoint as covered. Respect each
publisher/API's access and reuse terms; configured availability is not permission
to redistribute complete source content.
