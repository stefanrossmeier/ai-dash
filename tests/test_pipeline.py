from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from ai_dash.delivery import Rejected, flush
from ai_dash.models import Artifact, Coverage, Item, Settings, Source, Story
from ai_dash.presentation import render
from ai_dash.processing import canonical_url, deduplicate, identity, rank
from ai_dash.retrieval import _nitter_rss_items, parse_feed, retrieve_x, timestamp
from ai_dash.storage import Store, exclusive
from tests.ranking_helpers import FakeImpactRanker

NOW = datetime(2026, 11, 9, 18, tzinfo=UTC)


def source(**kwargs):
    return Source(
        id="test",
        name="Test",
        category="Lab",
        priority="P1",
        kind="feed",
        url="https://example.org",
        endpoint="https://example.org/rss",
        focus="AI",
        **kwargs,
    )


def item(title="A new model", url="https://example.org/news", published=None):
    return Item(
        id=identity(url),
        title=title,
        url=url,
        source_id="test",
        source="Test",
        category="Lab",
        priority="P1",
        published_at=published or NOW - timedelta(hours=1),
        text="New AI inference release with measured throughput and documented hardware support. "
        * 8,
    )


def artifact(stories=None):
    return Artifact(
        run_id="test-run",
        created_at=NOW,
        window_start=NOW - timedelta(hours=24),
        window_end=NOW,
        stories=stories or [Story(item=item(), score=80, summary="Useful news.")],
        candidates=[item()],
        coverage=[Coverage(source_id="test", status="ok")],
        traces=[],
        stats={},
    )


def test_dates_rfc822_iso_and_undated():
    assert timestamp("Mon, 09 Nov 2026 17:00:00 +0000") == NOW - timedelta(hours=1)
    assert timestamp("2026-11-09T17:00:00Z") == NOW - timedelta(hours=1)
    assert timestamp("2026-11-09").hour == 0
    assert timestamp("2026-11-09T17:00:00") is None
    assert timestamp("garbage") is None
    assert timestamp(None) is None


def test_rss_and_atom_keep_whitespace_and_require_dates():
    rss = """<rss><channel><item><title>A  new\n model</title><link>https://example.org/new</link>
    <pubDate>Mon, 09 Nov 2026 17:00:00 +0000</pubDate></item>
    <item><title>No date</title><link>https://example.org/old</link></item></channel></rss>"""
    items, raw = parse_feed(source(), rss, 25)
    assert raw == 2 and len(items) == 1
    assert items[0].title == "A new model"
    atom = """<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>An Atom model</title>
    <link href="https://example.org/atom"/><updated>2026-11-09T17:00:00Z</updated></entry></feed>"""
    items, raw = parse_feed(source(), atom, 25)
    assert raw == 1 and items[0].url == "https://example.org/atom"


def test_dedupe_window_boundaries_tracking_and_history():
    items = [
        item(),
        item(url="https://www.example.org/news/?utm_source=x#top"),
        item("Old", "https://example.org/old", NOW - timedelta(days=2)),
        item("Future", "https://example.org/future", NOW + timedelta(seconds=1)),
    ]
    assert len(deduplicate(items, NOW - timedelta(hours=24), NOW, [])) == 1
    assert (
        deduplicate(
            items, NOW - timedelta(hours=24), NOW, [{"url": item().url, "title": item().title}]
        )
        == []
    )
    assert canonical_url("https://twitter.com/Test/status/123?s=20").startswith("https://x.com/")


def test_ranking_rejects_invented_ids(tmp_path):
    prompt = tmp_path / "prompt.md"
    prompt.write_text("Use candidates only")

    class Fake:
        def request(self, *args):
            return {"content": {"evaluations": {"invented": {}}}}

    with pytest.raises(ValueError, match="unknown"):
        rank([item()], Settings(sources=[]), Fake(), prompt, [])


def test_ranking_processes_all_batches_without_provisional_history(tmp_path):
    import json

    prompt = tmp_path / "prompt.md"
    prompt.write_text("Use candidates only")
    gateway = FakeImpactRanker()
    items = [item(f"Model {n}", f"https://example.org/{n}") for n in range(5)]
    result = rank(items, Settings(sources=[], ranking_batch_size=2), gateway, prompt, [])
    calls = [
        json.loads(c["messages"][1]["content"])
        for c in gateway.calls
        if c["purpose"] == "ai-news-ranking"
    ]
    assert len(result) == 5 and len(calls) == 3
    assert calls[1]["already_covered"] == []


def test_nitter_rss_parses_full_timeline_into_items(monkeypatch):
    pub = (NOW - timedelta(hours=1)).strftime("%a, %d %b %Y %H:%M:%S GMT")
    feed = f"""<?xml version="1.0"?><rss><channel>
    <item><title>GPT-7 is out</title><link>https://nitter.mie.foundation/swyx/status/123</link>
    <guid>https://nitter.mie.foundation/swyx/status/123</guid><pubDate>{pub}</pubDate>
    <description>&lt;p&gt;GPT-7 is out, weights on HF&lt;/p&gt;</description></item>
    </channel></rss>"""

    class MockClient:
        def __init__(self, **kw):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def get(self, url):
            return SimpleNamespace(text=feed, raise_for_status=lambda: None)

    monkeypatch.setattr(httpx, "Client", MockClient)
    s = source().model_copy(update={"kind": "x", "url": "https://x.com/swyx"})
    items, error = _nitter_rss_items(s, Settings(sources=[s]), NOW)
    assert error is None and len(items) == 1
    # Nitter links map back to the canonical x.com status URL.
    assert items[0].url == "https://x.com/swyx/status/123"
    assert items[0].published_at == NOW - timedelta(hours=1)
    assert "GPT-7" in items[0].title


def test_storage_persistence_before_delivery_and_sent_history(tmp_path, monkeypatch):
    monkeypatch.setattr("ai_dash.delivery.time.sleep", lambda _: None)
    store = Store(tmp_path)
    art = artifact()
    path = store.persist(art, ["part one", "part two"], "@ai")
    assert path.exists()
    assert store.history(NOW, 14) == []
    calls = []

    class Fake:
        def call(self, method, data):
            assert path.exists()
            assert store.pending()[0][3] == "sending"
            calls.append(data["text"])
            return {"message_id": len(calls)}

    assert flush(store, Fake(), "@ai") == 2
    assert calls == ["part one", "part two"]
    assert len(store.history(NOW, 14)) == 1
    assert flush(store, Fake(), "@ai") == 0
    with pytest.raises(FileExistsError):
        store.persist(art, [], "@ai")
    store.close()


def test_uncertain_delivery_blocks_retry_until_resolution(tmp_path):
    store = Store(tmp_path)
    store.persist(artifact(), ["part"], "@ai")

    class Fake:
        def call(self, *args):
            raise RuntimeError("transport failed")

    with pytest.raises(RuntimeError, match="transport"):
        flush(store, Fake(), "@ai")
    assert store.pending()[0][3] == "sending"
    with pytest.raises(RuntimeError, match="uncertain"):
        flush(store, Fake(), "@ai")
    store.resolve("test-run", 0, "sent")
    assert store.pending() == []
    assert len(store.history(NOW, 14)) == 1
    store.close()


def test_rejected_send_stays_pending_and_not_deduped(tmp_path):
    store = Store(tmp_path)
    store.persist(artifact(), ["part"], "@ai")

    class Fake:
        def call(self, *args):
            raise Rejected("not allowed")

    with pytest.raises(Rejected):
        flush(store, Fake(), "@ai")
    assert store.pending()[0][3] == "pending"
    assert store.history(NOW, 14) == []
    with pytest.raises(RuntimeError, match="reroute"):
        flush(store, Fake(), "@different")
    store.close()


def test_process_lock_excludes_overlap(tmp_path):
    with exclusive(tmp_path):
        with pytest.raises(RuntimeError, match="lock"), exclusive(tmp_path):
            pass


def test_plain_text_story_boundaries_and_utf16_limits():
    stories = [
        Story(
            item=item("A model 😀" * 20, f"https://example.org/{n}"),
            score=80,
            summary="Summary 😀 " * 45,
        )
        for n in range(15)
    ]
    messages = render(artifact(stories), "Europe/Berlin")
    assert len(messages) > 1
    assert all(len(m.encode("utf-16-le")) // 2 <= 3900 for m in messages)
    for n in range(15):
        assert sum(f"https://example.org/{n}\n" in m + "\n" for m in messages) == 1


def test_registry_and_namespace_contract():
    import yaml

    from ai_dash.models import load_settings

    root = Path(__file__).resolve().parents[1]
    settings = load_settings(root / "config/sources.yaml")
    assert len(settings.sources) == 118
    assert all(s.kind != "x" or s.url.startswith("https://x.com/") for s in settings.sources)
    folder = root / "workflows/windmill/f/ai_dash"
    for path in folder.glob("*.schedule.yaml"):
        schedule = yaml.safe_load(path.read_text())
        assert schedule["enabled"] is False
        assert schedule["script_path"] in {
            "f/ai_dash/company",
            "f/ai_dash/blogs",
            "f/ai_dash/research_oss",
            "f/ai_dash/x_major",
            "f/ai_dash/singularity",
            "f/ai_dash/ai_news",
        }
        assert schedule["timezone"] == settings.timezone
        assert schedule["no_flow_overlap"] is True
    flow = yaml.safe_load((folder / "company__flow/flow.yaml").read_text())
    assert flow["value"]["modules"][0]["value"]["tag_override"] == "aidash"


def test_html_uses_only_publisher_advertised_feed():
    from ai_dash.retrieval import html_items

    class Response:
        text = """<rss><channel><item><title>A real release</title>
        <link>https://example.org/new</link><pubDate>Mon, 09 Nov 2026 17:00:00 +0000</pubDate>
        </item></channel></rss>"""
        content = text.encode()

        def raise_for_status(self):
            pass

    calls = []

    class Client:
        def get(self, url, **kwargs):
            calls.append(url)
            return Response()

    items, _ = html_items(
        source(),
        Client(),
        '<link rel="alternate" type="application/rss+xml" href="/actual-feed">',
        25,
    )
    assert calls == ["https://example.org/actual-feed"]
    assert len(items) == 1


def test_total_outage_is_failure_before_ranking(monkeypatch, tmp_path):
    from ai_dash.pipeline import build

    monkeypatch.setattr(
        "ai_dash.pipeline.collect",
        lambda *a, **k: ([], [Coverage(source_id="test", status="unavailable")]),
    )
    with pytest.raises(RuntimeError, match="no source"):
        build(Settings(sources=[]), object(), tmp_path / "unused", [])


def test_run_persists_before_send_and_second_run_dedupes(monkeypatch, tmp_path):
    from ai_dash.gateway import Gateway
    from ai_dash.pipeline import run

    monkeypatch.setattr("ai_dash.delivery.time.sleep", lambda _: None)
    monkeypatch.setattr(
        "ai_dash.pipeline.collect",
        lambda *a, **k: (
            [item(published=datetime.now(UTC) - timedelta(hours=1))],
            [Coverage(source_id="test", status="ok", items=1, fresh=1)],
        ),
    )
    monkeypatch.setattr(
        "ai_dash.pipeline.rank",
        lambda items, *a, **kw: [
            Story(item=i, score=80, summary="A useful announcement.") for i in items
        ],
    )

    class Fake:
        def check(self, target):
            assert target == "@new_ai"

        def call(self, method, data):
            assert list((tmp_path / "artifacts").rglob("*.json"))
            return {"message_id": 1}

    first = run(
        Settings(sources=[]),
        Gateway("http://unused"),
        tmp_path / "unused",
        tmp_path,
        Fake(),
        "@new_ai",
    )
    second = run(
        Settings(sources=[]),
        Gateway("http://unused"),
        tmp_path / "unused",
        tmp_path,
        Fake(),
        "@new_ai",
    )
    assert first["messages_sent"] == 1
    assert second["messages_sent"] == 0
    assert second["stats"]["candidates_unseen"] == 0


def test_telegram_errors_never_expose_token(monkeypatch):
    import httpx

    from ai_dash.delivery import Telegram

    def broken(*args, **kwargs):
        raise httpx.ConnectError("https://api.telegram.org/botSECRET/sendMessage")

    monkeypatch.setattr("ai_dash.delivery.httpx.post", broken)
    with pytest.raises(RuntimeError) as exc:
        Telegram("SECRET").call("sendMessage", {})
    assert "SECRET" not in str(exc.value)


def test_release_build_noise_filtered_and_feed_cap_keeps_newest():
    release = source().model_copy(update={"category": "GitHub"})
    content = """<rss><channel>
    <item><title>b12345: update build</title><link>https://example.org/build</link>
    <pubDate>Mon, 09 Nov 2026 18:00:00 +0000</pubDate></item>
    <item><title>v1.0</title><link>https://example.org/old</link>
    <pubDate>Sun, 08 Nov 2026 17:00:00 +0000</pubDate></item>
    <item><title>v2.0</title><link>https://example.org/new</link>
    <pubDate>Mon, 09 Nov 2026 17:00:00 +0000</pubDate></item></channel></rss>"""
    items, count = parse_feed(release, content, 1)
    assert count == 1 and items[0].title == "v2.0"


def test_x_rss_only_and_never_paid(monkeypatch):
    class Boom:
        def request(self, *args, **kwargs):
            raise AssertionError("paid X retrieval is parked; RSS is the only path")

    def fake_rss(source, settings, now):
        if source.id == "a":
            return ["an-item"], None
        return [], "instance down"

    monkeypatch.setattr("ai_dash.retrieval._nitter_rss_items", fake_rss)
    sources = [
        source().model_copy(update={"id": "a", "kind": "x", "url": "https://x.com/a"}),
        source().model_copy(update={"id": "b", "kind": "x", "url": "https://x.com/b"}),
    ]
    items, coverage = retrieve_x(sources, Settings(sources=sources), Boom(), NOW)
    # Serving handle timelines via free RSS: no sampling, no paid requests,
    # per-handle failure isolation instead of whole-batch loss.
    assert items == ["an-item"]
    assert coverage[0].status == "ok" and coverage[0].items == 1
    assert coverage[1].status == "unavailable" and coverage[1].detail == "instance down"


def test_ranking_requires_exact_keyed_slots(tmp_path):
    prompt = tmp_path / "prompt.md"
    prompt.write_text("Use supplied items")
    gateway = FakeImpactRanker()
    stories = rank([item()], Settings(sources=[]), gateway, prompt, [])
    schema = gateway.calls[0]["response_schema"]["properties"]["evaluations"]
    assert schema["required"] == ["c0"]
    assert schema["additionalProperties"] is False
    assert len(stories) == 1 and stories[0].item.id == item().id


def test_paper_cap_preserves_room_for_blogs_and_x(tmp_path):

    prompt = tmp_path / "prompt.md"
    prompt.write_text("Use candidates")
    paper = source().model_copy(update={"id": "papers", "url": "https://arxiv.org/list/cs.AI"})
    blog = source()
    items = [
        item(f"Paper {n}", f"https://arxiv.org/abs/{n}").model_copy(update={"source_id": "papers"})
        for n in range(10)
    ]
    items += [item("Company model release", "https://example.org/release")]

    stories = rank(
        items, Settings(sources=[paper, blog], max_paper_stories=6), FakeImpactRanker(), prompt, []
    )
    assert len(stories) == 7
    assert sum(s.item.source_id == "papers" for s in stories) == 6
    assert any(s.item.title == "Company model release" for s in stories)
