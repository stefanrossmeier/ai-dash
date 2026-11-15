"""Offline probes of audit findings; false values indicate repairs to the baseline.

Run from the repository root:
    PYTHONPATH=src .venv/bin/python docs/evidence/news-audit-reproduce.py
No network, model requests, delivery, or application state writes.
"""

import json
from datetime import UTC, datetime, timedelta

from ai_dash.models import Source
from ai_dash.processing import deduplicate
from ai_dash.retrieval import html_items, parse_feed

source = Source(
    id="audit",
    name="Audit",
    category="Analysis",
    url="https://example.org/blog",
    priority="P1",
    kind="feed",
    endpoint="https://example.org/feed",
    focus="AI engineering",
)
now = datetime(2026, 11, 15, 12, tzinfo=UTC)
feed = """<rss xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel>
<item><title>Agent evaluation breakthrough</title><link>https://example.org/new</link>
<pubDate>Sun, 15 Nov 2026 10:00:00 GMT</pubDate><description>Short teaser.</description>
<content:encoded><![CDATA[<p>Full substantive agent benchmark results and engineering facts.</p>]]>
</content:encoded></item></channel></rss>"""
item = parse_feed(source, feed, 25)[0][0]
results = {"feed_full_content_ignored": item.text == "Short teaser."}

release_source = source.model_copy(update={"category": "GitHub"})
prerelease = feed.replace("Agent evaluation breakthrough", "v0.34.0rc4")
results["rc_without_hyphen_not_filtered"] = bool(parse_feed(release_source, prerelease, 25)[0])

html = """<article><time datetime="2026-11-01">Nov 1</time>
<a href="/blog/old">Old lengthy article title</a></article>
<article><time datetime="2026-11-15">Nov 15</time>
<a href="/blog/new">New lengthy article title</a></article>"""
results["html_cap_keeps_old_before_new"] = (
    html_items(source, object(), html, 1)[0][0].title == "Old lengthy article title"
)

# A feed visible after a one-hour indexing delay can miss a once-daily report.
late = item.model_copy(update={"published_at": now - timedelta(hours=24, minutes=1)})
results["late_unseen_story_dropped"] = not deduplicate([late], now - timedelta(hours=24), now, [])

# Version-only release titles collide globally across unrelated projects.
one = item.model_copy(update={"title": "v1.0.0", "url": "https://example.org/project-a"})
two = item.model_copy(update={"title": "v1.0.0", "url": "https://example.org/project-b"})
results["unrelated_releases_collide_by_title"] = (
    len(deduplicate([one, two], now - timedelta(hours=24), now, [])) == 1
)

print(json.dumps(results, indent=2))
