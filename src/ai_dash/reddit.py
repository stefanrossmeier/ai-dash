"""Authenticated Reddit listings using ai-dash-owned private credential files."""

import html
import os
import re
import stat
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit

import httpx

from ai_dash.content import excerpt
from ai_dash.models import Coverage, Item, Settings, Source
from ai_dash.processing import canonical_url, identity


class RedditError(ValueError):
    pass


def private_value(name: str) -> str:
    path = os.getenv(f"AI_DASH_{name.upper()}_FILE", f"/run/ai-dash-secrets/{name}")
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
                raise RedditError("reddit_credentials_unavailable")
            value = stream.read(16385).decode().strip()
        if not value or len(value) > 16384 or "\n" in value or "\r" in value:
            raise RedditError("reddit_credentials_unavailable")
        return value
    except (OSError, UnicodeError):
        raise RedditError("reddit_credentials_unavailable") from None


def checked_json(response: httpx.Response, stage: str) -> dict:
    if response.is_error or response.is_redirect:
        raise RedditError(f"reddit_{stage}_http_{response.status_code}")
    if len(response.content) > 12_000_000:
        raise RedditError("reddit_response_too_large")
    payload = response.json()
    if not isinstance(payload, dict):
        raise RedditError("reddit_response_invalid")
    return payload


def retrieve_reddit(source: Source, settings: Settings, now: datetime):
    try:
        parsed = urlsplit(source.url)
        match = re.fullmatch(r"/r/([A-Za-z0-9_]{2,21})/?", parsed.path)
        if parsed.hostname not in {"reddit.com", "www.reddit.com"} or not match:
            raise RedditError("reddit_source_invalid")
        subreddit = match[1]
        client_id = private_value("reddit_client_id")
        secret = private_value("reddit_client_secret")
        user_agent = private_value("reddit_user_agent")
        cutoff = now - timedelta(hours=settings.freshness_hours)
        items, seen, after = [], set(), None
        scanned = 0
        with httpx.Client(
            timeout=settings.request_timeout,
            follow_redirects=False,
            trust_env=False,
            headers={"User-Agent": user_agent},
        ) as client:
            auth = checked_json(
                client.post(
                    "https://www.reddit.com/api/v1/access_token",
                    data={"grant_type": "client_credentials"},
                    auth=(client_id, secret),
                ),
                "oauth",
            )
            token = auth.get("access_token")
            if not isinstance(token, str) or not token:
                raise RedditError("reddit_oauth_token_missing")
            for _ in range(10):
                params = {"limit": 100, "raw_json": 1}
                if after:
                    params["after"] = after
                listing = checked_json(
                    client.get(
                        f"https://oauth.reddit.com/r/{subreddit}/new",
                        params=params,
                        headers={"Authorization": "Bearer " + token},
                    ),
                    "listing",
                )
                data = listing.get("data")
                if not isinstance(data, dict) or not isinstance(data.get("children"), list):
                    raise RedditError("reddit_listing_invalid")
                old = False
                for child in data["children"]:
                    row = child.get("data") if isinstance(child, dict) else None
                    if not isinstance(row, dict):
                        continue
                    scanned += 1
                    try:
                        created = datetime.fromtimestamp(float(row["created_utc"]), UTC)
                    except (KeyError, ValueError, TypeError, OverflowError, OSError):
                        continue
                    if created < cutoff:
                        old = True
                        continue
                    if created >= now or row.get("stickied") or row.get("removed_by_category"):
                        continue
                    title = html.unescape(str(row.get("title") or "")).strip()[:500]
                    permalink = row.get("permalink", "")
                    if (
                        not title
                        or not isinstance(permalink, str)
                        or not permalink.startswith(f"/r/{subreddit}/comments/")
                    ):
                        continue
                    url = canonical_url("https://www.reddit.com" + permalink)
                    if url in seen:
                        continue
                    seen.add(url)
                    crossposts = [
                        parent
                        for parent in (row.get("crosspost_parent_list") or [])[:3]
                        if isinstance(parent, dict)
                    ]
                    linked_url = ""
                    for target in [row.get("url"), *(p.get("url") for p in crossposts)]:
                        if not isinstance(target, str):
                            continue
                        target_url = urlsplit(target)
                        host = (target_url.hostname or "").removeprefix("www.")
                        if (
                            target_url.scheme in {"https", "http"}
                            and host
                            and host != "reddit.com"
                            and not host.endswith(".reddit.com")
                            and host != "redd.it"
                            and not host.endswith(".redd.it")
                            and target_url.username is None
                            and target_url.password is None
                        ):
                            linked_url = target
                            break
                    context = "\n".join(str(p.get("selftext") or "") for p in crossposts)
                    text = (
                        f"Community submission to r/{subreddit}, not independently verified. "
                        f"{title}\n{row.get('selftext') or ''}\n"
                        f"Crossposted discussion: {context}\n"
                        f"Linked source: {row.get('url') or url}"
                    )
                    items.append(
                        Item(
                            id=identity(url),
                            title=title,
                            url=url,
                            published_at=created,
                            source_id=source.id,
                            source=source.name,
                            category=source.category,
                            priority=source.priority,
                            text=excerpt(html.unescape(text)),
                            date_basis="submission",
                            linked_url=linked_url,
                        )
                    )
                    if len(items) >= settings.max_per_source:
                        break
                next_after = data.get("after")
                if old or len(items) >= settings.max_per_source or not next_after:
                    break
                if not isinstance(next_after, str) or next_after == after:
                    raise RedditError("reddit_pagination_invalid")
                after = next_after
        return items, Coverage(
            source_id=source.id,
            status="ok" if items else "empty",
            items=len(items),
            fresh=len(items),
            detail=f"oauth; scanned={scanned}; cap={settings.max_per_source}",
        )
    except RedditError as exc:
        detail = str(exc)
    except httpx.HTTPError:
        detail = "reddit_transport_failed"
    except (ValueError, KeyError, TypeError):
        detail = "reddit_response_invalid"
    return [], Coverage(source_id=source.id, status="unavailable", detail=detail)
