from __future__ import annotations

from zoneinfo import ZoneInfo

from ai_dash.models import Artifact


def render(artifact: Artifact, timezone: str) -> list[str]:
    """Plain text avoids markup injection. Split only at complete story boundaries."""
    if not artifact.stories and not (artifact.send_empty or artifact.example):
        return []
    header = (
        "AI Dash · "
        + artifact.report_title
        + (" · Example" if artifact.example else "")
        + " · "
        + artifact.created_at.astimezone(ZoneInfo(timezone)).strftime("%d %b %Y · %H:%M %Z")
    )
    if artifact.example and any(t.get("cached") for t in artifact.traces):
        header += "\nX results reused from today’s cache; no new paid retrieval."
    if not artifact.stories:
        hours = int((artifact.window_end - artifact.window_start).total_seconds() // 3600)
        return [
            header + f"\n\nNo new qualifying stories in the last {hours} hours. "
            "Already-delivered stories are omitted."
        ]
    messages = []
    current = header
    for number, story in enumerate(artifact.stories, 1):
        item = story.item
        date_label = {
            "publication": "Published",
            "submission": "Submitted",
            "curation": "Curated",
            "repository_update": "Repository updated",
        }[item.date_basis]
        dated = item.published_at.astimezone(ZoneInfo(timezone)).strftime("%d %b · %H:%M %Z")
        block = (
            f"{number}. {item.title}\n{story.summary}\n{item.source} · {item.category}\n"
            f"{date_label} {dated}\n{item.url}"
        )
        if len(block.encode("utf-16-le")) // 2 > 3500:
            raise ValueError("story exceeds Telegram message budget")
        proposed = current + "\n\n" + block
        if len(proposed.encode("utf-16-le")) // 2 > 3900:
            messages.append(current)
            current = header + " (continued)\n\n" + block
        else:
            current = proposed
    messages.append(current)
    return messages
