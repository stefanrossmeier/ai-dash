"""Bounded public article evidence; no model calls or publication-date invention."""

from __future__ import annotations

import ipaddress
import json
import socket
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup

from ai_dash.models import Item, Settings


def excerpt(value: str, limit: int = 12000) -> str:
    soup = BeautifulSoup(value, "html.parser")
    for node in soup.select("script, style, nav, footer, aside, form, svg"):
        node.decompose()
    text = " ".join(soup.get_text(" ").split())
    if len(text) <= limit:
        return text
    # Preserve evidence beyond newsletter intros without generating a paraphrase.
    size = (limit - 20) // 3
    middle = len(text) // 2
    return text[:size] + " [...] " + text[middle : middle + size] + " [...] " + text[-size:]


def public_url(url: str) -> None:
    parsed = urlsplit(url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.port not in {None, 80, 443}
    ):
        raise ValueError("unsupported article URL")
    addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(row[4][0]).is_global for row in addresses):
        raise ValueError("article host is not public")


def read_article(client: httpx.Client, url: str) -> str:
    for _ in range(5):
        public_url(url)
        with client.stream("GET", url, follow_redirects=False) as response:
            if response.is_redirect:
                url = urljoin(url, response.headers["location"])
                continue
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").split(";")[0]
            if content_type not in {"text/html", "text/plain", "text/markdown", ""}:
                raise ValueError("article is not readable text")
            chunks = []
            size = 0
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > 2_000_000:
                    raise ValueError("article exceeds evidence budget")
                chunks.append(chunk)
            return b"".join(chunks).decode(response.encoding or "utf-8", errors="replace")
    raise ValueError("too many article redirects")


def article_evidence(html: str) -> tuple[str, object]:
    soup = BeautifulSoup(html, "html.parser")
    meta = soup.select_one(
        'meta[property="article:published_time"], meta[name="date"], time[datetime]'
    )
    date = (meta.get("content") or meta.get("datetime")) if meta else None
    structured_text = []

    def walk(value):
        nonlocal date
        if isinstance(value, list):
            for child in value:
                walk(child)
        elif isinstance(value, dict):
            if value.get("datePublished") and (value.get("headline") or value.get("articleBody")):
                date = date or value["datePublished"]
            if isinstance(value.get("articleBody"), str):
                structured_text.append(value["articleBody"])
            for child in value.values():
                if isinstance(child, (dict, list)):
                    walk(child)

    for script in soup.select('script[type="application/ld+json"]'):
        try:
            walk(json.loads(script.string or "{}"))
        except (ValueError, TypeError):
            continue
    # Some publishers use <article> for only a header and .prose for the body.
    bodies = soup.select(".prose, .blog-content, #blog-content")
    roots = bodies or soup.select("article, main, [role=main]")
    # Never turn a navigation-only or subscription page into article evidence.
    text = max((excerpt(str(root)) for root in roots), key=len, default="")
    if structured_text:
        text = max([text, *(excerpt(t) for t in structured_text)], key=len)
    return text, date


def hydrate(items: list[Item], settings: Settings) -> tuple[list[Item], list[dict]]:
    from ai_dash.retrieval import timestamp

    targets = [
        i
        for i in items
        if (i.discovered_via or len(i.text) < 500 or i.date_basis == "repository_update")
        and urlsplit(i.url).hostname not in {"x.com", "twitter.com"}
    ][: settings.hydration_max_requests]
    target_ids = {i.id for i in targets}

    def one(item):
        url = item.url
        if urlsplit(url).hostname == "huggingface.co" and item.category in {
            "Model hub",
            "Discovery",
        }:
            url += "/raw/main/README.md"
        try:
            with httpx.Client(
                timeout=settings.hydration_timeout, headers={"User-Agent": "ai-dash/0.1"}
            ) as client:
                html = read_article(client, url)
            if url.endswith("/raw/main/README.md"):
                text, date = excerpt(html), None
            else:
                text, date = article_evidence(html)
            published = timestamp(date)
            if item.discovered_via and published is None:
                return None, {"stage": "hydration", "id": item.id, "status": "undated_link"}
            update = {}
            if item.discovered_via and published is not None:
                update.update(published_at=published, date_basis="publication")
            elif item.date_basis == "submission" and published is not None:
                update["original_published_at"] = published
            if len(text) > len(item.text):
                update["text"] = excerpt(item.text + "\n" + text)
            result = item.model_copy(update=update)
            return result, {
                "stage": "hydration",
                "id": item.id,
                "status": "hydrated" if update.get("text") else "no_body",
            }
        except (httpx.HTTPError, OSError, ValueError, KeyError) as exc:
            return (None if item.discovered_via else item), {
                "stage": "hydration",
                "id": item.id,
                "status": "unavailable",
                "detail": type(exc).__name__,
            }

    with ThreadPoolExecutor(max_workers=settings.workers) as pool:
        results = list(pool.map(one, targets))
    replacements = {i.id: result for i, (result, _) in zip(targets, results, strict=True)}
    hydrated = []
    for item in items:
        if item.discovered_via and item.id not in target_ids:
            continue  # Never send an unverified linked story after the fetch budget runs out.
        result = replacements.get(item.id, item)
        if result is not None:
            hydrated.append(result)
    return hydrated, [log for _, log in results]
