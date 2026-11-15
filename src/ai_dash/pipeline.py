from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from ai_dash.content import hydrate
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
    selection_log = []
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
    # Preserve failure diagnostics above, even during a total outage.
    if not any(c.status in {"ok", "empty"} for c in coverage):
        raise RuntimeError("no source produced dated items; refusing an empty successful edition")
    candidates = deduplicate(raw, start, now, history)
    candidates, hydration_log = hydrate(candidates, settings)
    selection_log.extend(hydration_log)
    # Linked articles must pass the window again using their verified publisher dates.
    candidates = deduplicate(candidates, start, now, history)
    evidence = [i for i in candidates if len(i.text.strip()) >= 80]
    selection_log.extend(
        {"stage": "evidence", "id": i.id, "status": "insufficient_evidence"}
        for i in candidates
        if i not in evidence
    )
    try:
        stories = rank(evidence, settings, gateway, prompt, history, audit=selection_log)
    finally:
        if checkpoint is not None:
            data = json.loads(checkpoint.read_text())
            data.update(
                selection_log=selection_log,
                candidates=[i.model_dump(mode="json") for i in candidates],
                traces=gateway.traces,
            )
            temporary = checkpoint.with_suffix(".tmp")
            temporary.write_text(json.dumps(data))
            temporary.replace(checkpoint)
    warnings = [
        f"source {c.source_id}: {c.status}"
        for c in coverage
        if c.status in {"unavailable", "undated", "search_required"}
    ]
    if len(evidence) < len(candidates):
        warnings.append(f"{len(candidates) - len(evidence)} candidates lack usable evidence")
    stats = {
        "items_dated": len(raw),
        "items_24h": sum(now - timedelta(hours=24) <= i.published_at < now for i in raw),
        "items_in_window": sum(start <= i.published_at < now for i in raw),
        "candidates_unseen": len(candidates),
        "candidates_evidenced": len(evidence),
        "candidates_ranked": sum(r["stage"] == "ranking" and "id" in r for r in selection_log),
        "candidates_policy_rejected": sum(r.get("status") == "rejected" for r in selection_log),
        "hydration_requests": len(hydration_log),
        "health_warnings": len(warnings),
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
        selection_log=selection_log,
        health_warnings=warnings,
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
            for warning in artifact.health_warnings:
                logging.warning("AI Dash %s: %s", settings.report_id, warning)
            return {
                "run_id": artifact.run_id,
                "artifact_path": str(path),
                "messages_sent": sent,
                "messages_resumed": resumed,
                "stats": artifact.stats,
                "health_warnings": artifact.health_warnings,
            }
        finally:
            store.close()
