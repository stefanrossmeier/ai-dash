"""Seed today's small watchlist cache from the already-paid, validated legacy collection.

Run once inside the worker. Never fetches X, resets a reservation, or sends a message.
"""

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ai_dash.models import Item, load_settings
from ai_dash.reports import load_reports, select_report
from ai_dash.x_budget import XDailyBudget

home = Path("/opt/ai-dash")
root = Path("/data/ai-dash")
checkpoint = root / "collection-latest.json"
settings = select_report(
    load_settings(home / "config/sources.yaml"),
    load_reports(home / "config/reports.yaml"),
    "x_major",
)
legacy = json.loads(checkpoint.read_text())
created = datetime.fromisoformat(legacy["created_at"])
budget = XDailyBudget(root, settings.timezone)
if created.astimezone(ZoneInfo(settings.timezone)).date().isoformat() != budget.day():
    raise SystemExit("Legacy collection is not from today; no cache was seeded.")
allowed = {s.id: s for s in settings.sources}
handles = [s.url.rsplit("/", 1)[-1] for s in settings.sources]
posts = []
for raw in legacy["items"]:
    item = Item.model_validate(raw)
    if item.source_id in allowed:
        posts.append(
            dict(
                author_handle=allowed[item.source_id].url.rsplit("/", 1)[-1],
                post_url=item.url,
                post_text=item.text,
            )
        )
existing = budget.cached_or_reserve(handles)
if existing is not None:
    print("Daily X cache already exists; preserved.")
else:
    response = dict(
        alias=settings.x_alias,
        provider="previously-validated-collection",
        model="cached",
        content={"posts": posts},
        usage={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cost_usd": 0.0},
        latency_ms=0,
        attempts=0,
        usage_complete=True,
        provider_metadata={
            "citation_urls": [p["post_url"] for p in posts],
            "reused_collection_at": legacy["created_at"],
        },
    )
    budget.save(handles, response)
    print(f"Reused {len(posts)} validated major-lab posts; no new X request.")
