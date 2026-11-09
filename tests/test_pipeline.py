from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ai_dash.delivery import Rejected, flush
from ai_dash.models import Artifact, Coverage, Item, Settings, Source, Story
from ai_dash.presentation import render
from ai_dash.processing import canonical_url, deduplicate, identity, rank
from ai_dash.retrieval import parse_feed, retrieve_x, timestamp
from ai_dash.storage import Store, exclusive

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
            return {
                "content": {
                    "decisions": [
                        {
                            "id": "invented",
                            "technical": 30,
                            "practical": 30,
                            "novelty": 20,
                            "impact": 20,
                            "summary": "Fake",
                        }
                    ]
                }
            }

    with pytest.raises(ValueError, match="unknown"):
        rank([item()], Settings(sources=[]), Fake(), prompt, [])


def test_ranking_processes_all_batches_and_carries_selected_context(tmp_path):
    import json

    prompt = tmp_path / "prompt.md"
    prompt.write_text("Use candidates only")
    calls = []

    class Fake:
        def request(self, route, payload):
            user = json.loads(payload["messages"][1]["content"])
            calls.append(user)
            return {
                "content": {
                    "decisions": [
                        dict(
                            id=c["id"],
                            technical=30,
                            practical=30,
                            novelty=20,
                            impact=20,
                            summary="New release.",
                        )
                        for c in user["candidates"]
                    ]
                }
            }

    items = [item(f"Model {n}", f"https://example.org/{n}") for n in range(5)]
    result = rank(items, Settings(sources=[], ranking_batch_size=2), Fake(), prompt, [])
    assert len(result) == 5 and len(calls) == 3
    assert len(calls[1]["already_covered"]) == 2


def test_x_accepts_only_cited_allowed_fresh_posts():
    snowflake = str((int((NOW - timedelta(hours=1)).timestamp() * 1000) - 1288834974657) << 22)
    url = f"https://x.com/test/status/{snowflake}"

    class Fake:
        def request(self, *args):
            return {
                "content": {
                    "posts": [
                        dict(author_handle="test", post_url=url, post_text="A real announcement"),
                        dict(author_handle="other", post_url=url, post_text="Wrong author"),
                        dict(
                            author_handle="test",
                            post_url="https://x.com/test/status/1",
                            post_text="Uncited",
                        ),
                    ]
                },
                "provider_metadata": {"citation_urls": [url]},
            }

    s = source().model_copy(update={"kind": "x", "url": "https://x.com/test"})
    items, coverage = retrieve_x([s], Settings(sources=[s]), Fake(), NOW)
    assert len(items) == 1 and coverage[0].fresh == 1
    assert items[0].published_at == NOW - timedelta(hours=1)


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
    assert len(settings.sources) == 95
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
        lambda items, *a: [
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


def test_x_timeout_retries_once_in_smaller_groups():
    calls = []

    class Fake:
        def request(self, route, body):
            calls.append(body["allowed_x_handles"])
            if len(calls) == 1:
                raise RuntimeError("timeout")
            return {"content": {"posts": []}, "provider_metadata": {"citation_urls": []}}

    sources = [
        source().model_copy(update={"id": f"x-{n}", "kind": "x", "url": f"https://x.com/test{n}"})
        for n in range(4)
    ]
    items, coverage = retrieve_x(sources, Settings(sources=sources), Fake(), NOW)
    assert [len(c) for c in calls] == [4, 2, 2]
    assert len(coverage) == 4 and all(c.status == "empty" for c in coverage)


def test_x_outage_retries_are_bounded():
    calls = []

    class Fake:
        def request(self, route, body):
            calls.append(body["allowed_x_handles"])
            raise RuntimeError("outage")

    sources = [
        source().model_copy(update={"id": f"x-{n}", "kind": "x", "url": f"https://x.com/test{n}"})
        for n in range(4)
    ]
    items, coverage = retrieve_x(sources, Settings(sources=sources), Fake(), NOW)
    assert len(calls) == 3
    assert len(coverage) == 4 and all(c.status == "unavailable" for c in coverage)


def test_ranking_constrains_ids_and_ignores_harmless_repetition(tmp_path):
    import json

    prompt = tmp_path / "prompt.md"
    prompt.write_text("Use supplied items")

    class Fake:
        def request(self, route, payload):
            candidates = json.loads(payload["messages"][1]["content"])["candidates"]
            assert payload["response_schema"]["$defs"]["Decision"]["properties"]["id"]["enum"] == [
                "c0"
            ]
            assert candidates[0]["id"] == "c0"
            decision = dict(
                id="c0",
                technical=30,
                practical=30,
                novelty=20,
                impact=20,
                summary="A useful release.",
            )
            return {"content": {"decisions": [decision, decision]}}

    stories = rank([item()], Settings(sources=[]), Fake(), prompt, [])
    assert len(stories) == 1 and stories[0].item.id == item().id


def test_paper_cap_preserves_room_for_blogs_and_x(tmp_path):
    import json

    prompt = tmp_path / "prompt.md"
    prompt.write_text("Use candidates")
    paper = source().model_copy(update={"id": "papers", "url": "https://arxiv.org/list/cs.AI"})
    blog = source()
    items = [
        item(f"Paper {n}", f"https://arxiv.org/abs/{n}").model_copy(update={"source_id": "papers"})
        for n in range(10)
    ]
    items += [item("Company model release", "https://example.org/release")]

    class Fake:
        def request(self, route, body):
            candidates = json.loads(body["messages"][1]["content"])["candidates"]
            return {
                "content": {
                    "decisions": [
                        dict(
                            id=c["id"],
                            technical=30,
                            practical=30 if c["source_id"] == "papers" else 20,
                            novelty=20,
                            impact=20,
                            summary="A material development.",
                        )
                        for c in candidates
                    ]
                }
            }

    stories = rank(items, Settings(sources=[paper, blog], max_paper_stories=6), Fake(), prompt, [])
    assert len(stories) == 7
    assert sum(s.item.source_id == "papers" for s in stories) == 6
    assert any(s.item.title == "Company model release" for s in stories)
