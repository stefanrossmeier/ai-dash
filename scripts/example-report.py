"""Render a synthetic artifact without networking, credentials or persistent state."""

from datetime import UTC, datetime, timedelta

from ai_dash.models import Artifact, Item, Story
from ai_dash.presentation import render

now = datetime(2026, 1, 1, 12, tzinfo=UTC)
item = Item(
    id="synthetic-example",
    title="SYNTHETIC EXAMPLE: an AI development would appear here",
    url="https://example.invalid/synthetic-announcement",
    published_at=now - timedelta(hours=1),
    source_id="synthetic-source",
    source="Synthetic source",
    category="Example",
    priority="P1",
    text="This is invented format-demonstration content, not a news item.",
)
artifact = Artifact(
    run_id="synthetic-format-example",
    report_id="synthetic",
    report_title="Synthetic format example",
    example=True,
    created_at=now,
    window_start=now - timedelta(hours=25),
    window_end=now,
    stories=[
        Story(
            item=item,
            score=0,
            summary=(
                "This synthetic text shows where a concise explanation and its significance "
                "would appear. Real reports attribute claims and preserve uncertainty. "
                "No news was collected, no model was called, and no Telegram message "
                "was sent to produce this local example."
            ),
        )
    ],
    candidates=[item],
    coverage=[],
    traces=[],
    stats={"selected": 1},
)
for message in render(artifact, "Europe/Berlin"):
    print(message)
