from __future__ import annotations

import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import feedparser
import httpx
from bs4 import BeautifulSoup

from ai_dash.content import article_evidence, excerpt
from ai_dash.gateway import Gateway
from ai_dash.models import (
    Coverage,
    Item,
    Settings,
    Source,
    YouTubeChannel,
    load_youtube_channels,
)
from ai_dash.network import bounded_get, public_client
from ai_dash.processing import canonical_url, identity
from ai_dash.reddit import retrieve_reddit

AI_WORDS = re.compile(
    r"\b(ai|llm|llms|gpt|claude|gemini|inference|transformer|transformers|agent|agents|"
    r"neural|machine learning|deep learning|language model|gpu|cuda|quantization|"
    r"diffusion|qwen|deepseek|llama|mistral|hugging|rag|vllm|sglang|openai|anthropic|"
    r"codex|copilot|cursor|reasoning|fine-tuning|post-training|jev)\b",
    re.I,
)


def timestamp(value: object) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        result = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        try:
            result = parsedate_to_datetime(value.strip())
        except (TypeError, ValueError, OverflowError):
            return None
    if result.tzinfo is None:
        # Date-only API fields mean midnight UTC, not local discovery time.
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value.strip()):
            result = result.replace(tzinfo=UTC)
        else:
            return None
    return result.astimezone(UTC)


def plain(value: str) -> str:
    return " ".join(
        (BeautifulSoup(value, "html.parser").get_text(" ") if "<" in value else value).split()
    )


def make_item(source: Source, title: str, url: str, date: object, text: str = "") -> Item | None:
    dt = timestamp(date)
    if dt is None or not title.strip():
        return None
    return Item(
        id=identity(url),
        title=plain(title)[:500],
        url=canonical_url(url),
        published_at=dt,
        source_id=source.id,
        source=source.name,
        category=source.category,
        priority=source.priority,
        text=excerpt(text),
    )


def fetch(client: httpx.Client, url: str, **kwargs) -> httpx.Response:
    # Full browser UA for Reddit: it 403s plain "Mozilla/5.0" and bot UAs from
    # datacenter IPs; the full Chrome string passes (verified live 2026-11-16).
    # Everything else keeps the default client UA.
    if (urlsplit(url).hostname or "").removeprefix("www.") == "reddit.com":
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
            ),
            "Accept": "application/rss+xml,application/xml,text/xml,*/*",
        }
    else:
        headers = {}
    return bounded_get(client, url, headers=headers, **kwargs)


def parse_feed(source: Source, content: str, cap: int) -> tuple[list[Item], int]:
    feed = feedparser.parse(content)
    entries = feed.entries
    if not entries and feed.bozo:
        raise ValueError("invalid feed")
    # Some publisher feeds are not chronologically ordered. Cap after sorting/filtering.
    eligible = [
        e
        for e in entries
        if not (
            source.category == "GitHub"
            and re.search(
                r"^b\d+(?::.*)?$|(?:\d[.-]?|[-.])(?:rc|alpha|beta|dev|preview)\.?\d*\b",
                e.get("title", ""),
                re.I,
            )
        )
    ]
    eligible.sort(
        key=lambda e: (
            timestamp(e.get("published") or e.get("updated")) or datetime.min.replace(tzinfo=UTC)
        ),
        reverse=True,
    )
    selected = eligible[:cap]
    items = []
    for e in selected:
        date = e.get("published") or e.get("updated")
        bodies = [e.get("summary", ""), *(c.get("value", "") for c in e.get("content", []))]
        body = max(bodies, key=lambda value: len(plain(value)))
        item = make_item(source, e.get("title", ""), e.get("link", ""), date, body)
        if item:
            if source.expand_roundups and item.title.startswith("[AINews]"):
                item = item.model_copy(update={"category": "Aggregator"})
                # Roundup links are discovery hints. Hydration must establish the
                # linked publisher's date before any of these can be selected.
                links = {}
                for anchor in BeautifulSoup(body, "html.parser").select("a[href]"):
                    url = urljoin(item.url, str(anchor["href"]))
                    host = (urlsplit(url).hostname or "").removeprefix("www.")
                    title = plain(anchor.get_text(" "))
                    if (
                        urlsplit(url).scheme in {"https", "http"}
                        and host not in {"latent.space", "x.com", "twitter.com", "discord.com"}
                        and len(title) >= 20
                        and len(title.split()) >= 4
                    ):
                        links.setdefault(canonical_url(url), title)
                for url, title in list(links.items())[:8]:
                    child = make_item(source, title, url, date)
                    if child:
                        items.append(
                            child.model_copy(
                                update={
                                    "discovered_via": item.url,
                                    "source": f"{urlsplit(url).hostname} (via {source.name})",
                                    "category": "Aggregator",
                                }
                            )
                        )
            items.append(item)
    if source.category == "GitHub":
        items = items[:3]
    return items, len(selected)


def html_items(source: Source, client: httpx.Client, text: str, cap: int) -> tuple[list[Item], int]:
    soup = BeautifulSoup(text, "html.parser")
    # Prefer publisher-declared RSS/Atom endpoints, without guessing endpoint paths.
    for link in soup.select('link[rel="alternate"]'):
        if link.get("type") in {"application/rss+xml", "application/atom+xml"}:
            endpoint = urljoin(source.endpoint, str(link.get("href", "")))
            if urlsplit(endpoint).hostname == urlsplit(source.endpoint).hostname:
                return parse_feed(source, fetch(client, endpoint).text, cap)
    items = []
    # Newsroom feature cards can point outside /news/ and carry their date in <time>.
    # Trust the publisher's dated article structure, never the discovery/crawl date.
    for block in soup.find_all("article"):
        date_node = block.find("time")
        if date_node is None:
            continue
        date_raw = str(date_node.get("datetime") or date_node.get_text(" ", strip=True))
        date = timestamp(date_raw)
        if date is None:
            for fmt in ("%b %d, %Y", "%B %d, %Y"):
                try:
                    date = datetime.strptime(date_raw, fmt).replace(tzinfo=UTC)
                    break
                except ValueError:
                    continue
        if date is None:
            continue
        for anchor in block.find_all("a", href=True):
            title = plain(anchor.get_text(" "))
            url = urljoin(source.url, str(anchor["href"]))
            if (
                len(title) < 18
                or urlsplit(url).scheme not in {"http", "https"}
                or (urlsplit(url).hostname or "").removeprefix("www.")
                != (urlsplit(source.url).hostname or "").removeprefix("www.")
            ):
                continue
            item = make_item(source, title, url, date.isoformat(), block.get_text(" ", strip=True))
            if item:
                items.append(item)
                break

    def walk(value):
        if isinstance(value, list):
            for v in value:
                walk(v)
        elif isinstance(value, dict):
            if value.get("datePublished") and (value.get("headline") or value.get("name")):
                url = value.get("url") or value.get("mainEntityOfPage") or source.url
                if isinstance(url, dict):
                    url = url.get("@id", source.url)
                item = make_item(
                    source,
                    value.get("headline") or value["name"],
                    urljoin(source.url, url),
                    value["datePublished"],
                    value.get("description", ""),
                )
                if item:
                    items.append(item)
            for v in value.values():
                if isinstance(v, (dict, list)):
                    walk(v)

    for script in soup.select('script[type="application/ld+json"]'):
        try:
            walk(json.loads(script.string or "{}"))
        except (ValueError, TypeError, KeyError):
            continue
    # Date verification is a hard gate: visit actual article links for metadata.
    base = urlsplit(source.url)
    links = {}
    known_urls = {i.url for i in items}
    for anchor in soup.select("a[href]"):
        url = urljoin(source.url, str(anchor["href"]))
        p = urlsplit(url)
        title = plain(anchor.get_text(" "))
        if (
            p.hostname == base.hostname
            and any(
                p.path.startswith(path.rstrip("/") + "/")
                for path in (source.article_paths or [base.path])
            )
            and p.path != base.path
            and len(title) >= 18
            and not p.fragment
            and canonical_url(url) not in known_urls
        ):
            links.setdefault(url, title)
    for url, title in list(links.items())[: min(cap, 8)]:
        try:
            article_html = fetch(client, url).text
            article = BeautifulSoup(article_html, "html.parser")
            meta = article.select_one(
                'meta[property="article:published_time"], meta[name="date"], time[datetime]'
            )
            date = meta.get("content") or meta.get("datetime") if meta else None
            if date is None:
                for script in article.select('script[type="application/ld+json"]'):
                    walk(json.loads(script.string or "{}"))
                continue
            description = article.select_one('meta[name="description"]')
            body, _ = article_evidence(article_html)
            item = make_item(
                source,
                title,
                url,
                date,
                body or (str(description.get("content", "")) if description else ""),
            )
            if item:
                items.append(item)
        except (httpx.HTTPError, ValueError, TypeError):
            continue
    unique = {i.url: i for i in items}
    return sorted(unique.values(), key=lambda i: i.published_at, reverse=True)[:cap], len(
        links
    ) + len(unique)


def retrieve_one(
    source: Source, settings: Settings, now: datetime
) -> tuple[list[Item], Coverage | list[Coverage]]:
    if not source.enabled or source.kind == "manual":
        return [], Coverage(
            source_id=source.id,
            status="disabled" if not source.enabled else "manual",
            detail=source.note,
        )
    if source.kind == "x":
        return [], Coverage(source_id=source.id, status="search_required")
    if source.kind == "youtube":
        return retrieve_youtube(source, settings, now)
    if source.kind == "reddit":
        return retrieve_reddit(source, settings, now)
    cutoff = now - timedelta(hours=settings.freshness_hours)
    for attempt in range(2):
        try:
            with public_client(
                timeout=settings.request_timeout,
                follow_redirects=True,
                headers={
                    "User-Agent": "ai-dash/0.1 (+AI-news-reader)",
                    "Accept-Encoding": "identity",
                },
            ) as client:
                # Passing even an empty dict to httpx replaces the URL's query,
                # dropping configured author, sorting and limit filters.
                params = None
                if source.kind == "hn":
                    params = {
                        "tags": "story",
                        "numericFilters": f"created_at_i>{int(cutoff.timestamp())},points>20",
                        "hitsPerPage": 100,
                    }
                elif source.kind == "github":
                    params = {
                        "q": f"topic:llm pushed:>={cutoff.date()} stars:>20 archived:false",
                        "sort": "stars",
                        "per_page": 25,
                    }
                response = fetch(client, source.endpoint, params=params)
                if source.kind == "feed":
                    items, raw_count = parse_feed(source, response.text, settings.max_per_source)
                elif source.kind == "html":
                    items, raw_count = html_items(
                        source, client, response.text, settings.max_per_source
                    )
                else:
                    data = response.json()
                    rows = data.get("hits", []) if source.kind == "hn" else data
                    if source.kind == "github":
                        rows = data.get("items", [])
                    items = []
                    raw_count = 0
                    for row in rows:
                        if len(items) >= settings.max_per_source:
                            break
                        if source.kind == "hn":
                            title, url, date = (
                                row.get("title", ""),
                                row.get("url"),
                                row.get("created_at"),
                            )
                            if not AI_WORDS.search(title):
                                continue
                            url = url or f"https://news.ycombinator.com/item?id={row['objectID']}"
                            text = ""
                        elif source.kind == "hf_papers":
                            paper = row["paper"]
                            title, url = (
                                paper["title"],
                                "https://huggingface.co/papers/" + paper["id"],
                            )
                            date = row.get("publishedAt") or paper.get("publishedAt")
                            text = (
                                "Community paper curation, not necessarily new research. "
                                f"Original publication: {paper.get('publishedAt', 'unknown')}. "
                                + paper.get("summary", "")
                            )
                        elif source.kind == "hf_models":
                            title = row.get("id", row.get("modelId", ""))
                            url, date = (
                                "https://huggingface.co/" + title,
                                row.get("lastModified") or row.get("createdAt"),
                            )
                            text = (
                                "Model repository update; neither creation nor modification "
                                "establishes "
                                "a new model release. " + str(row.get("pipeline_tag", ""))
                            )
                        else:
                            title, url = row["full_name"], row["html_url"]
                            date = row.get("pushed_at") or row["created_at"]
                            text = "Recently active repository, not a verified release. " + (
                                row.get("description") or ""
                            )
                            if not AI_WORDS.search(title + " " + text):
                                continue
                        raw_count += 1
                        item = make_item(source, title, url, date, text)
                        if item:
                            if source.kind in {"hf_models", "github"}:
                                item = item.model_copy(update={"date_basis": "repository_update"})
                            elif source.kind == "hf_papers":
                                item = item.model_copy(
                                    update={
                                        "date_basis": "curation",
                                        "original_published_at": timestamp(
                                            paper.get("publishedAt")
                                        ),
                                    }
                                )
                            elif source.kind == "hn":
                                item = item.model_copy(update={"date_basis": "submission"})
                            items.append(item)
            status = "ok" if items else ("undated" if raw_count else "empty")
            if status != "ok" and attempt == 0:
                continue
            return items, Coverage(
                source_id=source.id,
                status=status,
                items=len(items),
                fresh=sum(cutoff <= i.published_at < now for i in items),
            )
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            if attempt == 0:
                time.sleep(0.3)
                continue
            # Do not include request URLs (credentials could be embedded by a transport).
            return [], Coverage(
                source_id=source.id, status="unavailable", detail=type(exc).__name__
            )
    raise AssertionError("unreachable")


def parse_youtube_feed(
    source: Source, channel: YouTubeChannel, content: str, now: datetime, freshness_hours: int
) -> list[Item]:
    feed = feedparser.parse(content)
    if not feed.entries and feed.bozo:
        raise ValueError("invalid YouTube feed")
    author = plain(feed.feed.get("author", "")) or channel.display_name
    channel_source = source.model_copy(update={"name": author})
    cutoff = now - timedelta(hours=freshness_hours)
    items = []
    for entry in feed.entries:
        video_id = entry.get("yt_videoid")
        if not video_id:
            raw_id = str(entry.get("id", ""))
            if raw_id.startswith("yt:video:"):
                video_id = raw_id.removeprefix("yt:video:")
        published = timestamp(entry.get("published") or entry.get("updated"))
        title = plain(entry.get("title", ""))
        if not video_id or not title or published is None or not cutoff <= published < now:
            continue
        url = f"https://www.youtube.com/watch?v={video_id}"
        items.append(
            Item(
                id=identity(url),
                title=title[:500],
                url=url,
                published_at=published,
                source_id=source.id,
                source=channel_source.name,
                category=source.category,
                priority=source.priority,
            )
        )
    return sorted(items, key=lambda item: item.published_at, reverse=True)


def retrieve_youtube(
    source: Source, settings: Settings, now: datetime
) -> tuple[list[Item], list[Coverage]]:
    home = Path(os.getenv("AI_DASH_HOME", "."))
    channels = load_youtube_channels(home / str(source.channel_config))

    def collect_channel(channel: YouTubeChannel) -> tuple[list[Item], Coverage]:
        coverage_id = f"{source.id}:{channel.id}"
        if not channel.enabled:
            return [], Coverage(source_id=coverage_id, status="disabled")
        try:
            with public_client(
                timeout=settings.request_timeout,
                follow_redirects=True,
                headers={"User-Agent": "ai-dash/0.1 (+AI-news-reader)"},
            ) as client:
                response = fetch(
                    client,
                    source.endpoint,
                    params={"channel_id": channel.channel_id},
                )
            items = parse_youtube_feed(
                source, channel, response.text, now, settings.freshness_hours
            )
            return items, Coverage(
                source_id=coverage_id,
                status="ok" if items else "empty",
                items=len(items),
                fresh=len(items),
            )
        except (httpx.HTTPError, OSError, ValueError, TypeError) as exc:
            return [], Coverage(
                source_id=coverage_id,
                status="unavailable",
                detail=type(exc).__name__,
            )

    with ThreadPoolExecutor(max_workers=settings.workers) as pool:
        results = list(pool.map(collect_channel, channels))
    return (
        [item for items, _ in results for item in items],
        [coverage for _, coverage in results],
    )


# Free Nitter RSS instances, tried in order. Instances are volunteer-run and
# die often (xcancel 451, nitter.net 410); mie.foundation verified live
# 2026-11-19. A plain bot User-Agent gets an HTML shell; a browser UA is required.
NITTER_INSTANCES = (
    "https://nitter.mie.foundation",
    "https://nitter.netbub.com",
)
NITTER_UA = "Mozilla/5.0 (X11; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0"


def _nitter_status_url(link: str) -> str:
    # Nitter links carry the host; map back to the canonical x.com status URL.
    parts = urlsplit(link)
    if "status" not in parts.path:
        return link
    handle = parts.path.strip("/").split("/")[0]
    status = parts.path.strip("/").split("/")[-1].split("#")[0]
    return f"https://x.com/{handle}/status/{status}"


def _nitter_rss_items(
    source: Source, settings: Settings, now: datetime
) -> tuple[list[Item], str | None]:
    """Full timeline for one handle via free Nitter RSS. Returns items plus an
    error string (None on success). RSS is the account's actual timeline - no
    search recall loss, no per-account sampling cap, no paid request."""
    handle = source.url.rstrip("/").rsplit("/", 1)[-1]
    error = None
    for instance in NITTER_INSTANCES:
        url = f"{instance}/{handle}/rss"
        try:
            with public_client(
                timeout=settings.request_timeout,
                follow_redirects=True,
                headers={"User-Agent": NITTER_UA, "Accept-Encoding": "identity"},
            ) as client:
                response = fetch(client, url)
                feed = feedparser.parse(response.text)
            if feed.bozo and not feed.entries:
                raise ValueError("invalid nitter feed")
            cutoff = now - timedelta(hours=settings.freshness_hours)
            items = []
            for entry in sorted(
                feed.entries,
                key=lambda e: timestamp(e.get("published")) or datetime.min.replace(tzinfo=UTC),
                reverse=True,
            ):
                if len(items) >= settings.max_per_source:
                    break
                date = timestamp(entry.get("published"))
                if date is not None and date < cutoff:
                    continue
                bodies = [
                    entry.get("summary", ""),
                    *(c.get("value", "") for c in entry.get("content", [])),
                ]
                body = max(bodies, key=lambda value: len(plain(value)))
                text = plain(body)
                item = make_item(
                    source,
                    (entry.get("title") or text)[: settings.ranking_excerpt_chars],
                    _nitter_status_url(entry.get("link", "")),
                    entry.get("published"),
                    text[: settings.ranking_excerpt_chars],
                )
                if item:
                    items.append(item)
            if items or feed.entries:
                return items, None
            raise ValueError("empty nitter feed")
        except Exception as exc:  # instance down / handle blocked / timeout
            error = f"{instance}: {type(exc).__name__}"
    return [], error


def retrieve_x(
    sources: list[Source],
    settings: Settings,
    gateway: Gateway,
    now: datetime,
) -> tuple[list[Item], list[Coverage]]:
    if len(sources) > 14:
        raise ValueError("X retrieval is limited to fourteen accounts")
    # Free Nitter RSS only (decision 2026-11-19): grok retrieval is parked for
    # the normal runs - the daily X report costs nothing while instances serve
    # the timelines, and a paid path cannot silently starve the report. RSS
    # serves full per-account timelines with no search recall loss and no
    # sampling cap; a handle an instance cannot serve is reported unavailable
    # (verified live 2026-11-19: 13 of 14 watchlist handles work on RSS).
    items: list[Item] = []
    coverage: list[Coverage] = []
    for source in sources:
        rss_items, error = _nitter_rss_items(source, settings, now)
        if error is None:
            items.extend(rss_items)
            coverage.append(Coverage(source_id=source.id, status="ok", items=len(rss_items)))
        else:
            coverage.append(
                Coverage(source_id=source.id, status="unavailable", detail=error, items=0)
            )
    return items, coverage


def collect(settings: Settings, gateway: Gateway, now: datetime, *, no_x: bool = False):
    with ThreadPoolExecutor(max_workers=settings.workers) as pool:
        results = list(
            pool.map(lambda source: retrieve_one(source, settings, now), settings.sources)
        )
    items = [item for batch, _ in results for item in batch]
    coverage = [
        row for _, status in results for row in (status if isinstance(status, list) else [status])
    ]
    x_sources = [s for s in settings.sources if s.kind == "x" and s.enabled]
    if settings.x_enabled and not no_x and x_sources:
        x_items, x_coverage = retrieve_x(x_sources, settings, gateway, now)
        items.extend(x_items)
        coverage = [c for c in coverage if c.status != "search_required"] + x_coverage
    return items, coverage
