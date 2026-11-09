from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from ai_dash.delivery import Telegram, flush
from ai_dash.gateway import Gateway
from ai_dash.models import Artifact, Settings
from ai_dash.presentation import render
from ai_dash.processing import deduplicate, rank
from ai_dash.retrieval import collect
from ai_dash.storage import Store, exclusive


def build(
    settings: Settings,
    gateway: Gateway,
    prompt: Path,
    history: list[dict],
    *,
    no_x: bool = False,
    checkpoint: Path | None = None,
) -> Artifact:
    now = datetime.now(UTC)
    start = now - timedelta(hours=settings.freshness_hours)
    raw, coverage = collect(settings, gateway, now, no_x=no_x)
    # A total outage must fail, not masquerade as a quiet news day.
    if not any(c.status == "ok" for c in coverage) and not (
        settings.x_enabled and any(c.status == "empty" for c in coverage)
    ):
        raise RuntimeError("no source produced dated items; refusing an empty successful edition")
    if checkpoint is not None:
        temporary = checkpoint.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(
                {
                    "created_at": now.isoformat(),
                    "items": [i.model_dump(mode="json") for i in raw],
                    "coverage": [c.model_dump(mode="json") for c in coverage],
                    "traces": gateway.traces,
                }
            )
        )
        temporary.replace(checkpoint)
    candidates = deduplicate(raw, start, now, history)
    stories = rank(candidates, settings, gateway, prompt, history)
    stats = {
        "items_dated": len(raw),
        "items_24h": sum(start <= i.published_at < now for i in raw),
        "candidates_unseen": len(candidates),
        "selected": len(stories),
    }
    for status in (
        "ok",
        "empty",
        "unavailable",
        "undated",
        "manual",
        "search_required",
        "disabled",
    ):
        stats["sources_" + status] = sum(c.status == status for c in coverage)
    return Artifact(
        report_id=settings.report_id,
        report_title=settings.report_title,
        send_empty=settings.send_empty,
        example=settings.example,
        run_id=now.strftime("%Y%m%dT%H%M%SZ-") + uuid4().hex[:10],
        created_at=now,
        window_start=start,
        window_end=now,
        stories=stories,
        candidates=candidates,
        coverage=coverage,
        traces=gateway.traces,
        stats=stats,
    )


def run(
    settings: Settings,
    gateway: Gateway,
    prompt: Path,
    data_dir: Path,
    telegram: Telegram,
    destination: str,
    *,
    no_x: bool = False,
) -> dict:
    with exclusive(data_dir):
        store = Store(data_dir)
        try:
            telegram.check(destination)
            resumed = flush(store, telegram, destination)
            if settings.report_id == "x_major" and store.delivered_report_today(
                settings.report_id, datetime.now(UTC), settings.timezone
            ):
                return {
                    "report_id": settings.report_id,
                    "skipped": "already delivered today",
                    "messages_sent": 0,
                    "messages_resumed": resumed,
                }
            history = store.history(datetime.now(UTC), settings.history_days)
            artifact = build(
                settings,
                gateway,
                prompt,
                history,
                no_x=no_x,
                checkpoint=data_dir / f"collection-{settings.report_id}-latest.json",
            )
            messages = render(artifact, settings.timezone)
            path = store.persist(artifact, messages, destination)
            sent = flush(store, telegram, destination)
            return {
                "run_id": artifact.run_id,
                "artifact_path": str(path),
                "messages_sent": sent,
                "messages_resumed": resumed,
                "stats": artifact.stats,
            }
        finally:
            store.close()
