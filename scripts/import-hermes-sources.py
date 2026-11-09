"""Import a captured authoritative registry; endpoint adaptations are explicit."""

import re
from pathlib import Path

import yaml

root = Path(__file__).resolve().parents[1]
feed_endpoints = {
    "AI News / smol.ai": "https://latent.space/feeds/all.xml",
    "OpenAI News (RSS)": "https://openai.com/news/rss.xml",
    "Google DeepMind Blog (RSS)": "https://deepmind.google/blog/rss.xml",
    "Google AI Blog (RSS)": "https://blog.google/technology/ai/rss/",
    "Mistral News (RSS)": "https://mistral.ai/rss.xml",
    "Cursor Changelog (RSS)": "https://cursor.com/changelog/rss.xml",
    "NVIDIA Developer Blog (RSS)": "https://developer.nvidia.com/blog/feed/",
    "Databricks Blog (RSS)": "https://www.databricks.com/feed",
    "Simon Willison": "https://simonwillison.net/atom/everything/",
    "SemiAnalysis": "https://newsletter.semianalysis.com/feed",
    "Interconnects": "https://www.interconnects.ai/feed",
    "Ahead of AI": "https://magazine.sebastianraschka.com/feed",
    "Latent Space": "https://www.latent.space/feed",
    "r/LocalLLaMA": "https://www.reddit.com/r/LocalLLaMA/new.rss?limit=25",
}
sources = []
for row in (root / "docs/hermes-sources.md").read_text().splitlines():
    if not row.startswith("|"):
        continue
    cols = [s.strip() for s in row.strip("|").split("|")]
    if len(cols) != 5 or cols[4] not in {"P1", "P2"}:
        continue
    category, name, url, focus, priority = cols
    endpoint, kind, note = url, "html", ""
    if category.startswith("X /"):
        kind = "x"
    elif name in feed_endpoints:
        kind, endpoint = "feed", feed_endpoints[name]
    elif category == "GitHub":
        kind, endpoint = "feed", url + ".atom"
    elif category == "Research" and name.startswith("arXiv"):
        kind = "feed"
        cat = name.split()[-1]
        endpoint = "https://rss.arxiv.org/atom/" + cat
    elif name == "Hacker News":
        kind, endpoint = "hn", "https://hn.algolia.com/api/v1/search_by_date"
    elif name == "Hugging Face Papers":
        kind, endpoint = "hf_papers", "https://huggingface.co/api/daily_papers?limit=40"
    elif name == "Hugging Face Trending Models":
        kind = "hf_models"
        endpoint = (
            "https://huggingface.co/api/models?sort=trendingScore&direction=-1&limit=25&full=true"
        )
    elif category == "Model hub":
        kind = "hf_models"
        endpoint = (
            "https://huggingface.co/api/models?author="
            + url.rsplit("/", 1)[-1]
            + "&sort=createdAt&direction=-1&limit=25&full=true"
        )
    elif name == "GitHub Trending":
        kind, endpoint = "github", "https://api.github.com/search/repositories"
    elif category == "Benchmark":
        kind = "manual"
        note = (
            "Undated live leaderboard; not treated as a news feed. "
            "Related X accounts are separate sources."
        )
    if name == "AI News / smol.ai":
        note = (
            "Original URL redirects to latent.space/news/. Uses the publisher-advertised "
            "all-content feed; duplicates with Latent Space are removed during processing."
        )
    elif name.startswith("arXiv"):
        note = (
            "Official category Atom feed; API endpoint returned HTTP errors during VPS validation."
        )
    if kind == "x":
        note = (
            "Archived Hermes watchlist entry. Paid retrieval is allowed only "
            "through the explicit small daily X report."
        )
    source_id = re.sub("[^a-z0-9]+", "-", category.lower() + "-" + name.lower()).strip("-")
    sources.append(
        dict(
            id=source_id,
            name=name,
            category=category,
            url=url,
            priority=priority,
            kind=kind,
            endpoint=endpoint,
            focus=focus,
            enabled=kind != "x",
            note=note,
        )
    )
(root / "config/sources.yaml").write_text(
    yaml.safe_dump(
        dict(
            timezone="Europe/Berlin",
            slots=["07:30", "12:30", "17:30", "21:30"],
            freshness_hours=24,
            max_stories=30,
            max_paper_stories=6,
            min_score=55,
            x_enabled=False,
            sources=sources,
        ),
        sort_keys=False,
        allow_unicode=True,
    )
)
print(f"Imported {len(sources)} sources from docs/hermes-sources.md")
