from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from ai_dash.gateway import Gateway
from ai_dash.models import Item, Selection, Settings, Story


def canonical_url(url: str) -> str:
    p = urlsplit(url.strip())
    host = (p.hostname or "").lower().removeprefix("www.")
    host = "x.com" if host == "twitter.com" else host
    query = urlencode(
        sorted(
            (k, v)
            for k, v in parse_qsl(p.query)
            if not k.lower().startswith("utm_")
            and k.lower() not in {"ref", "source", "fbclid", "gclid"}
        )
    )
    path = p.path.rstrip("/")
    if host == "x.com":
        query = ""
        path = path.split("/photo/")[0].split("/video/")[0].lower()
    return urlunsplit(("https", host, path, query, ""))


def title_key(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.casefold()).strip()


def identity(url: str) -> str:
    return hashlib.sha256(canonical_url(url).encode()).hexdigest()[:24]


def deduplicate(
    items: list[Item], start: datetime, end: datetime, history: list[dict]
) -> list[Item]:
    urls = {canonical_url(x["url"]) for x in history}
    titles = {title_key(x["title"]) for x in history}
    result = []
    for item in sorted(items, key=lambda x: (x.priority != "P1", -x.published_at.timestamp())):
        url, title = canonical_url(item.url), title_key(item.title)
        if not start <= item.published_at < end or url in urls or title in titles:
            continue
        urls.add(url)
        titles.add(title)
        result.append(item.model_copy(update={"url": url, "id": identity(url)}))
    return result


def rank(
    items: list[Item], settings: Settings, gateway: Gateway, prompt: Path, history: list[dict]
) -> list[Story]:
    stories = []
    # Feed every candidate to a bounded ranking batch; do not silently truncate the pool.
    for offset in range(0, len(items), settings.ranking_batch_size):
        batch = items[offset : offset + settings.ranking_batch_size]
        context = history[-120:] + [{"title": s.item.title, "url": s.item.url} for s in stories]
        # Short batch-local IDs reduce transcription errors. Enum constrains provider output.
        by_id = {f"c{n}": item for n, item in enumerate(batch)}
        schema = Selection.model_json_schema()
        schema["$defs"]["Decision"]["properties"]["id"]["enum"] = list(by_id)
        schema["properties"]["decisions"]["maxItems"] = len(batch)
        response = gateway.request(
            "chat",
            {
                "alias": settings.ranking_alias,
                "purpose": "ai-news-ranking",
                "profile": "ai-dash",
                "messages": [
                    {
                        "role": "system",
                        "content": prompt.read_text()
                        + "\nReport focus: "
                        + settings.editorial_focus,
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "already_covered": context,
                                "candidates": [
                                    dict(i.model_dump(mode="json"), id=key)
                                    for key, i in by_id.items()
                                ],
                            }
                        ),
                    },
                ],
                "response_schema_name": "ai_dash_selection_v1",
                "response_schema": schema,
            },
        )
        selection = Selection.model_validate(response["content"])
        seen = set()
        for decision in selection.decisions:
            if decision.id not in by_id:
                raise ValueError("ranking returned an unknown candidate id")
            if decision.id in seen:
                continue
            seen.add(decision.id)
            if decision.score >= settings.min_score:
                stories.append(
                    Story(item=by_id[decision.id], score=decision.score, summary=decision.summary)
                )
    stories.sort(
        key=lambda s: (
            -s.score,
            s.item.category in {"Aggregator", "Community"},
            -s.item.published_at.timestamp(),
            s.item.id,
        )
    )
    paper_sources = {
        source.id
        for source in settings.sources
        if source.kind == "hf_papers" or (urlsplit(source.url).hostname or "").endswith("arxiv.org")
    }
    selected = []
    papers = 0
    for story in stories:
        is_paper = story.item.source_id in paper_sources
        if is_paper and papers >= settings.max_paper_stories:
            continue
        selected.append(story)
        papers += int(is_paper)
        if len(selected) >= settings.max_stories:
            break
    return selected
