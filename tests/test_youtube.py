from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
import yaml
from pydantic import ValidationError

from ai_dash.models import Coverage, Item, Settings, Source, YouTubeChannel
from ai_dash.pipeline import build
from ai_dash.presentation import render
from ai_dash.retrieval import collect, parse_youtube_feed

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 11, 10, 18, 30, tzinfo=UTC)
FEED = (ROOT / "tests/fixtures/youtube_feed.xml").read_text()


def youtube_source(**kwargs):
    return Source(
        id="youtube-channels",
        name="YouTube Channels",
        category="YouTube",
        priority="P1",
        kind="youtube",
        url="https://www.youtube.com/",
        endpoint="https://www.youtube.com/feeds/videos.xml",
        focus="New uploads",
        channel_config="youtube_channels.yaml",
        **kwargs,
    )


def channel(channel_id="UCLKPca3kwwd-B59HNr-_lvA", channel_name="Fixture Channel"):
    return YouTubeChannel(
        id="fixture",
        display_name=channel_name,
        handle="@fixture",
        channel_id=channel_id,
    )


def test_youtube_feed_parses_fixture_and_canonicalizes_shorts():
    items = parse_youtube_feed(youtube_source(), channel(), FEED, NOW, 24)

    assert [item.title for item in items] == ["A new short video", "A regular video"]
    assert items[0].source == "Fixture Channel"
    assert items[0].url == "https://www.youtube.com/watch?v=shortAbc1234"
    assert items[1].url == "https://www.youtube.com/watch?v=videoDef5678"
    assert all(item.url.startswith("https://www.youtube.com/watch?v=") for item in items)


def test_youtube_feed_excludes_entries_older_than_24_hours():
    items = parse_youtube_feed(youtube_source(), channel(), FEED, NOW, 24)

    assert all(item.title != "Outside the rolling window" for item in items)
    assert len(items) == 2


def test_youtube_channel_ids_are_validated():
    with pytest.raises(ValidationError, match="channel_id"):
        channel(channel_id="not-a-channel-id")


def test_youtube_channel_failures_are_isolated_and_reported(tmp_path, monkeypatch):
    channel_config = [
        {
            "id": "working",
            "display_name": "Working Channel",
            "handle": "@working",
            "channel_id": "UCLKPca3kwwd-B59HNr-_lvA",
            "enabled": True,
        },
        {
            "id": "broken",
            "display_name": "Broken Channel",
            "handle": "@broken",
            "channel_id": "UCdoTbckiMelGtWvGMfhlkgQ",
            "enabled": True,
        },
    ]
    (tmp_path / "youtube_channels.yaml").write_text(yaml.safe_dump({"channels": channel_config}))
    monkeypatch.setenv("AI_DASH_HOME", str(tmp_path))

    class Response:
        text = FEED
        content = FEED.encode()

        def raise_for_status(self):
            pass

    class MockClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def get(self, url, *, params, headers):
            assert url == "https://www.youtube.com/feeds/videos.xml"
            if params["channel_id"] == "UCdoTbckiMelGtWvGMfhlkgQ":
                raise httpx.ConnectError("channel unavailable")
            return Response()

    monkeypatch.setattr("ai_dash.retrieval.httpx.Client", MockClient)
    items, coverage = collect(
        Settings(sources=[youtube_source()]),
        SimpleNamespace(),
        NOW,
    )

    assert len(items) == 2
    assert {row.source_id: row.status for row in coverage} == {
        "youtube-channels:working": "ok",
        "youtube-channels:broken": "unavailable",
    }


def test_no_llm_build_uses_rolling_window_without_gateway_calls(monkeypatch, tmp_path):
    from ai_dash import pipeline

    run_at = datetime(2026, 11, 10, 18, 30, tzinfo=UTC)

    class FrozenDateTime:
        @staticmethod
        def now(tz):
            return run_at

    class NoGateway:
        traces = [{"purpose": "must not appear"}]

        def request(self, *args, **kwargs):
            pytest.fail("no-LLM report made a gateway request")

    def item(title, published_at):
        url = f"https://www.youtube.com/watch?v={title.replace(' ', '')}"
        return Item(
            id=title,
            title=title,
            url=url,
            published_at=published_at,
            source_id="youtube-channels",
            source="Fixture Channel",
            category="YouTube",
            priority="P1",
        )

    collected = [
        item("Prior-day 19:45", run_at - timedelta(hours=23, minutes=45)),
        item("Newest", run_at - timedelta(hours=1)),
        item("Earlier than prior-day 19:45", run_at - timedelta(hours=23, minutes=50)),
        item("Just outside", run_at - timedelta(hours=24, minutes=1)),
    ]
    monkeypatch.setattr(pipeline, "datetime", FrozenDateTime)
    monkeypatch.setattr(
        pipeline,
        "collect",
        lambda *args, **kwargs: (
            collected,
            [Coverage(source_id="youtube-channels:fixture", status="ok", items=4, fresh=3)],
        ),
    )
    monkeypatch.setattr(
        pipeline, "hydrate", lambda *args, **kwargs: pytest.fail("hydrate() must be skipped")
    )
    monkeypatch.setattr(
        pipeline, "rank", lambda *args, **kwargs: pytest.fail("rank() must be skipped")
    )

    artifact = build(
        Settings(
            sources=[youtube_source()],
            no_llm=True,
            report_id="youtube",
            report_title="YouTube — New Videos",
            max_stories=2,
            freshness_hours=24,
        ),
        NoGateway(),
        tmp_path / "unused-prompt.md",
        [],
    )

    assert [story.item.title for story in artifact.stories] == [
        "Newest",
        "Prior-day 19:45",
    ]
    assert len(artifact.candidates) == 3
    assert artifact.traces == [] and artifact.selection_log == []
    assert all(story.summary == "" for story in artifact.stories)
    message = render(artifact, "Europe/Berlin")[0]
    assert "Prior-day 19:45\nFixture Channel\nPublished 09 Nov · 19:45 CET" in message
    assert "\n\nFixture Channel" not in message
    assert "Just outside" not in message
