"""Regressions for production news loss, using HTTP fixtures and no model/network calls."""

import json
import runpy
import socket
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from ai_dash.content import article_evidence, excerpt, hydrate, public_url, read_article
from ai_dash.gateway import Gateway
from ai_dash.models import Coverage, Item, Settings, Source, load_settings
from ai_dash.pipeline import build, run
from ai_dash.presentation import render
from ai_dash.processing import deduplicate, identity, rank
from ai_dash.reports import load_reports, select_report
from ai_dash.retrieval import html_items, parse_feed, retrieve_one
from ai_dash.storage import Store
from tests.ranking_helpers import FakeImpactRanker as FakeRanker

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 11, 15, 12, tzinfo=UTC)
FACTS = "New AI agent runtime supports verified tool execution with measured latency reductions. "


def source(**updates):
    return Source.model_validate(
        dict(
            id="test",
            name="Test",
            category="Analysis",
            priority="P1",
            kind="feed",
            url="https://example.org/blog",
            endpoint="https://example.org/feed",
            focus="AI",
        )
        | updates
    )


def item(n=0, **updates):
    url = f"https://example.org/story-{n}"
    return Item.model_validate(
        dict(
            id=identity(url),
            title=f"Important AI engineering development number {n}",
            url=url,
            source_id="test",
            source="Test",
            category="Analysis",
            priority="P1",
            published_at=NOW - timedelta(hours=1),
            text=FACTS * 8,
        )
        | updates
    )


def feed_entry(title, date="Sun, 15 Nov 2026 10:00:00 GMT", body="", summary="Teaser."):
    return (
        f"<item><title>{title}</title><link>https://example.org/{title}</link>"
        f"<pubDate>{date}</pubDate><description>{summary}</description>"
        f"<content:encoded><![CDATA[{body}]]></content:encoded></item>"
    )


def feed(*entries):
    return (
        '<rss xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel>'
        + "".join(entries)
        + "</channel></rss>"
    )


@pytest.fixture
def prompt(tmp_path):
    path = tmp_path / "editorial.md"
    path.write_text("Use only supplied evidence; score every candidate.")
    return path


def test_feed_prefers_full_body_over_teaser_and_preserves_late_sections():
    body = (
        "Introduction. " * 1500 + "Middle evidence. " * 1500 + "Final benchmark findings. " * 1000
    )
    items, _ = parse_feed(source(), feed(feed_entry("New-model", body=body)), 25)
    assert "Middle evidence" in items[0].text
    assert "Final benchmark findings" in items[0].text
    assert "Teaser" not in items[0].text
    assert len(items[0].text) <= 12000


@pytest.mark.parametrize(
    "version", ["v0.34.0rc4", "v1.0-rc.1", "0.171.0-alpha.5", "v2.0beta2", "b12345: build"]
)
def test_prereleases_do_not_displace_stable_release(version):
    xml = feed(feed_entry(version), feed_entry("v1.0.0", "Sat, 14 Nov 2026 10:00:00 GMT"))
    items, _ = parse_feed(source(category="GitHub"), xml, 1)
    assert [i.title for i in items] == ["v1.0.0"]


def test_html_sorts_pinned_cards_before_cap_and_deduplicates():
    html = """<article><time datetime="2026-11-01">Nov 1</time>
    <a href="/old">Pinned older engineering article</a></article>
    <article><time datetime="2026-11-15">Nov 15</time>
    <a href="/new">New important engineering article</a></article>"""
    items, _ = html_items(source(), object(), html, 1)
    assert items[0].url == "https://example.org/new"


def test_roundup_links_require_long_titles_and_external_publishers():
    body = (
        '<p><a href="https://lab.example/new">'
        "New agent evaluation with reproducible benchmarks</a></p>"
    )
    body += (
        '<a href="https://x.com/test/status/1">Original agent evaluation with benchmarks here</a>'
    )
    body += '<a href="https://lab.example/other">click here</a>'
    items, _ = parse_feed(
        source(expand_roundups=True), feed(feed_entry("[AINews] Daily", body=body)), 25
    )
    children = [i for i in items if i.discovered_via]
    assert len(children) == 1 and children[0].url == "https://lab.example/new"
    assert children[0].text == ""
    assert next(i for i in items if not i.discovered_via).category == "Aggregator"


def test_article_uses_body_not_navigation_or_scripts():
    html = f"""<nav>Ignore navigation</nav><main><article>{FACTS * 10}</article></main>
    <script>Ignore script</script>
    <meta property="article:published_time" content="2026-11-15T10:00:00Z">"""
    text, date = article_evidence(html)
    assert FACTS.strip() in text and "Ignore" not in text
    assert date == "2026-11-15T10:00:00Z"
    text, date = article_evidence(
        '<script type="application/ld+json">'
        + json.dumps(
            {
                "headline": "A release",
                "datePublished": "2026-11-15",
                "articleBody": FACTS * 10,
            }
        )
        + "</script>"
    )
    assert len(text) > 500 and date == "2026-11-15"


def test_hydration_enriches_empty_hn_and_preserves_submission_provenance(monkeypatch):
    monkeypatch.setattr(
        "ai_dash.content.read_article",
        lambda *args: (
            f'<article>{FACTS * 12}</article><time datetime="2026-11-14T10:00:00Z">Yesterday</time>'
        ),
    )
    original = item(text="", date_basis="submission")
    result, log = hydrate([original], Settings(sources=[]))
    assert len(result[0].text) > 500
    assert result[0].published_at == original.published_at
    assert result[0].original_published_at == datetime(2026, 11, 14, 10, tzinfo=UTC)
    assert log[0]["status"] == "hydrated"


def test_hydration_budget_does_not_send_unverified_roundup_links(monkeypatch):
    monkeypatch.setattr(
        "ai_dash.content.read_article",
        lambda *a: (
            f'<article>{FACTS * 12}</article><time datetime="2026-11-15T10:00:00Z">Today</time>'
        ),
    )
    items = [item(n, text="", discovered_via="https://digest.example/issue") for n in range(3)]
    result, log = hydrate(items, Settings(sources=[], hydration_max_requests=1))
    assert len(result) == len(log) == 1
    assert result[0].published_at == datetime(2026, 11, 15, 10, tzinfo=UTC)
    monkeypatch.setattr(
        "ai_dash.content.read_article", lambda *a: f"<article>{FACTS * 12}</article>"
    )
    result, log = hydrate(items[:1], Settings(sources=[]))
    assert result == [] and log[0]["status"] == "undated_link"


def test_hydration_failure_retains_original_evidence_without_error_urls(monkeypatch):
    def failed(*args):
        raise httpx.ConnectError("https://secret.example/token")

    monkeypatch.setattr("ai_dash.content.read_article", failed)
    result, log = hydrate([item(text="Short evidence")], Settings(sources=[]))
    assert result[0].text == "Short evidence"
    assert "secret" not in json.dumps(log)


def test_model_card_hydration_retains_repository_update_warning(monkeypatch):
    calls = []

    def read(client, url):
        calls.append(url)
        return FACTS * 10

    monkeypatch.setattr("ai_dash.content.read_article", read)
    result, _ = hydrate(
        [
            item(
                url="https://huggingface.co/lab/model",
                category="Model hub",
                date_basis="repository_update",
                text="Repository update, not a release.",
            )
        ],
        Settings(sources=[]),
    )
    assert calls == ["https://huggingface.co/lab/model/raw/main/README.md"]
    assert result[0].text.startswith("Repository update, not a release.")


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/private",
        "http://127.0.0.1",
        "https://[::1]/",
        "https://user:pass@example.org",
        "file:///etc/passwd",
        "https://example.org:8080",
    ],
)
def test_public_article_reader_rejects_private_or_credentialled_urls(monkeypatch, url):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))],
    )
    with pytest.raises(ValueError):
        public_url(url)


def test_article_redirect_is_checked_before_following_and_size_is_bounded(monkeypatch):
    visited = []

    def public(url):
        visited.append(url)
        if "127.0.0.1" in url:
            raise ValueError("private")

    monkeypatch.setattr("ai_dash.content.public_url", public)

    def handler(request):
        return httpx.Response(302, headers={"location": "http://127.0.0.1/private"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ValueError, match="private"):
            read_article(client, "https://example.org/redirect")
    assert visited == ["https://example.org/redirect", "http://127.0.0.1/private"]
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(
                200, headers={"content-type": "text/html"}, content=b"x" * 2_000_001
            )
        )
    ) as client:
        with pytest.raises(ValueError, match="budget"):
            read_article(client, "https://example.org/large")


def test_generic_versions_and_non_latin_titles_do_not_collide():
    items = [
        item(0, title="v1.0.0"),
        item(1, title="v1.0.0"),
        item(2, title="新模型"),
        item(3, title="研究结果"),
    ]
    assert len(deduplicate(items, NOW - timedelta(days=1), NOW, [])) == 4
    history = [{"url": items[0].url, "title": "v1.0.0"}]
    assert len(deduplicate(items, NOW - timedelta(days=1), NOW, history)) == 3


def test_duplicate_urls_keep_richer_evidence():
    empty, rich = item(text=""), item(text=FACTS * 8)
    assert deduplicate([empty, rich], NOW - timedelta(days=1), NOW, [])[0].text == rich.text


def test_consolidation_prefers_later_primary_without_provisional_history(prompt):
    gateway = FakeRanker(groups=[dict(representative="s1", duplicates=["s0"])])
    history = [{"title": "Already delivered event", "url": "https://old.example/event"}]
    result = rank(
        [item(0, category="Aggregator"), item(1, category="Lab")],
        Settings(sources=[], ranking_batch_size=1),
        gateway,
        prompt,
        history,
    )
    assert [s.item.id for s in result] == [item(1).id]
    scoring = [c for c in gateway.calls if c["purpose"] == "ai-news-ranking"]
    assert all(
        json.loads(c["messages"][1]["content"])["already_covered"]
        == [{"title": h["title"]} for h in history]
        for c in scoring
    )


def test_missing_rank_decisions_fail_instead_of_silent_quiet_day(prompt):
    class Omitted:
        def request(self, *args):
            return {"content": {"decisions": []}}

    log = []
    with pytest.raises(ValueError, match="omitted"):
        rank([item()], Settings(sources=[]), Omitted(), prompt, [], audit=log)
    assert log[0]["status"] == "model_omitted"


def test_consolidation_cannot_drop_or_repeat_events(prompt):
    gateway = FakeRanker(groups=[dict(representative="s0", duplicates=[])])
    with pytest.raises(ValueError, match="every candidate"):
        rank([item(0), item(1)], Settings(sources=[]), gateway, prompt, [])


def test_selection_prefers_diverse_publishers_but_backfills(prompt):
    items = [item(n) for n in range(5)] + [item(5, url="https://other.example/event")]
    result = rank(items, Settings(sources=[], max_stories=4), FakeRanker(), prompt, [])
    assert any(s.item.url.startswith("https://other.example") for s in result)
    result = rank(items[:5], Settings(sources=[], max_stories=5), FakeRanker(), prompt, [])
    assert len(result) == 5


def test_ranking_rejection_scores_and_reasons_are_auditable(prompt):
    log = []
    assert rank([item()], Settings(sources=[]), FakeRanker(score=50), prompt, [], audit=log) == []
    assert log[0]["score"] == 50
    assert log[0]["status"] == "rejected"
    assert {"low_impact", "below_threshold"} <= set(log[0]["rejection_reasons"])
    assert log[0]["policy"] == "ai-impact-v2"


def test_outage_checkpoint_exists_before_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "ai_dash.pipeline.collect",
        lambda *a, **kw: ([], [Coverage(source_id="test", status="unavailable")]),
    )
    checkpoint = tmp_path / "collection.json"
    with pytest.raises(RuntimeError, match="no source"):
        build(
            Settings(sources=[]),
            Gateway("http://unused"),
            tmp_path / "unused",
            [],
            checkpoint=checkpoint,
        )
    assert json.loads(checkpoint.read_text())["coverage"][0]["status"] == "unavailable"


def test_empty_evidence_is_logged_without_model_or_send(monkeypatch, tmp_path, prompt):
    monkeypatch.setattr(
        "ai_dash.pipeline.collect",
        lambda *a, **kw: ([item(text="")], [Coverage(source_id="test", status="ok")]),
    )
    gateway = FakeRanker()
    artifact = build(
        Settings(sources=[], hydration_max_requests=0, freshness_hours=168), gateway, prompt, []
    )
    assert artifact.stories == [] and gateway.calls == []
    assert artifact.selection_log[0]["status"] == "insufficient_evidence"
    assert artifact.health_warnings


def test_end_to_end_multiple_message_delivery_and_history(monkeypatch, tmp_path, prompt):
    now = datetime.now(UTC)
    items = [item(n, published_at=now - timedelta(hours=1)) for n in range(12)]
    monkeypatch.setattr(
        "ai_dash.pipeline.collect",
        lambda *a, **kw: (items, [Coverage(source_id="test", status="ok", items=12, fresh=12)]),
    )
    monkeypatch.setattr("ai_dash.delivery.time.sleep", lambda _: None)
    messages = []

    class Telegram:
        def check(self, target):
            pass

        def call(self, method, body):
            assert list((tmp_path / "artifacts").rglob("*.json"))
            messages.append(body["text"])
            return {"message_id": len(messages)}

    opts = Settings(sources=[], max_stories=12)
    first = run(opts, FakeRanker(), prompt, tmp_path, Telegram(), "@test")
    second = run(opts, FakeRanker(), prompt, tmp_path, Telegram(), "@test")
    assert first["messages_sent"] >= 2 and second["messages_sent"] == 0
    store = Store(tmp_path)
    assert len(store.history(now, 14)) == 12
    assert store.pending() == []
    assert store.status()["reports"]["legacy"]["selected"] == 0
    store.close()
    assert all(len(m.encode("utf-16-le")) // 2 <= 3900 for m in messages)


def test_schedule_updates_preserve_other_reports_and_respect_pauses():
    policy = runpy.run_path(str(ROOT / "scripts/register-windmill.py"))["should_enable"]
    report = {"id": "company", "enabled": True}
    assert policy(report, False, ["blogs"], current_enabled=True)
    assert policy(report, False, [], current_enabled=True)
    assert not policy(report, False, [])
    assert not policy(report, True, [], current_enabled=True, disabled=["company"])
    assert not policy(report | {"enabled": False}, True, [], current_enabled=True)


def test_sources_and_catchup_are_enabled_without_changing_x_budget():
    settings = load_settings(ROOT / "config/sources.yaml")
    reports = load_reports(ROOT / "config/reports.yaml")
    groups = {r.id: select_report(settings, reports, r.id) for r in reports.reports}
    assert groups["blogs"].freshness_hours == 168
    assert groups["company"].freshness_hours == 48
    assert groups["research_oss"].freshness_hours == 72
    assert groups["x_major"].freshness_hours == 24
    assert groups["x_major"].max_per_source == 3 and not groups["x_major"].x_retry_split
    assert "analysis-latent-space" not in {s.id for s in groups["blogs"].sources}
    assert {"analysis-the-decoder", "analysis-import-ai"} <= {s.id for s in groups["blogs"].sources}


@pytest.mark.parametrize("kind", ["github", "hf_models", "hf_papers"])
def test_discovery_uses_activity_or_curation_dates_without_claiming_new_release(monkeypatch, kind):
    original_client = httpx.Client
    requests = []

    def handler(request):
        requests.append(request)
        if kind == "github":
            return httpx.Response(
                200,
                json={
                    "items": [
                        dict(
                            full_name="org/llm",
                            html_url="https://github.com/org/llm",
                            description=FACTS,
                            created_at="2025-01-01T00:00:00Z",
                            pushed_at="2026-11-15T10:00:00Z",
                        )
                    ]
                },
            )
        if kind == "hf_models":
            return httpx.Response(
                200,
                json=[
                    dict(
                        id="lab/model",
                        createdAt="2025-01-01T00:00:00Z",
                        lastModified="2026-11-15T10:00:00Z",
                    )
                ],
            )
        return httpx.Response(
            200,
            json=[
                dict(
                    publishedAt="2026-11-15T10:00:00Z",
                    paper=dict(
                        id="1234.5678",
                        title="Newly curated research",
                        publishedAt="2025-01-01T00:00:00Z",
                        summary=FACTS,
                    ),
                )
            ],
        )

    monkeypatch.setattr(
        "ai_dash.retrieval.httpx.Client",
        lambda **kw: original_client(transport=httpx.MockTransport(handler), **kw),
    )
    endpoint = "https://example.org/api?author=Qwen&sort=lastModified&limit=25"
    items, coverage = retrieve_one(source(kind=kind, endpoint=endpoint), Settings(sources=[]), NOW)
    assert len(items) == coverage.fresh == 1
    assert items[0].published_at == datetime(2026, 11, 15, 10, tzinfo=UTC)
    if kind == "github":
        assert "pushed:" in requests[0].url.params["q"]
        assert "created:" not in requests[0].url.params["q"]
    if kind == "hf_papers":
        assert items[0].date_basis == "curation"
        assert items[0].original_published_at.year == 2025
    else:
        assert items[0].date_basis == "repository_update"
    if kind != "github":
        assert requests[0].url.params["author"] == "Qwen"
        assert requests[0].url.params["sort"] == "lastModified"


def test_excerpt_removes_markup_without_exceeding_budget():
    assert excerpt("<p>Evidence</p><script>injected</script>") == "Evidence"
    assert len(excerpt("x" * 30000)) <= 12000


def test_html_cards_do_not_hide_newer_link_discovery():
    html = """<article><time datetime="2026-11-01">Old</time>
    <a href="/blog/old">Older pinned engineering article</a></article>
    <a href="/blog/new">Newer important engineering article</a>"""

    class Client:
        def get(self, url, **kw):
            assert url == "https://example.org/blog/new"
            return httpx.Response(
                200,
                request=httpx.Request("GET", url),
                text='<meta property="article:published_time" content="2026-11-15T10:00:00Z">'
                f"<article>{FACTS * 10}</article>",
            )

    items, _ = html_items(source(), Client(), html, 1)
    assert len(items) == 1 and items[0].url == "https://example.org/blog/new"


def test_catchup_stories_show_true_event_date_and_basis(monkeypatch, prompt):
    now = datetime.now(UTC)
    older = item(published_at=now - timedelta(hours=50), date_basis="repository_update")
    monkeypatch.setattr(
        "ai_dash.pipeline.collect",
        lambda *a, **kw: ([older], [Coverage(source_id="test", status="ok")]),
    )
    artifact = build(Settings(sources=[], freshness_hours=72), FakeRanker(), prompt, [])
    assert len(artifact.stories) == 1
    assert artifact.stats["items_24h"] == 0 and artifact.stats["items_in_window"] == 1
    assert "Repository updated" in render(artifact, "Europe/Berlin")[0]


def test_linked_papers_cannot_bypass_report_paper_cap(prompt):
    papers = [
        item(0, url="https://arxiv.org/abs/1234.5678", category="Aggregator"),
        item(1, url="https://huggingface.co/papers/1234.5678", category="Aggregator"),
    ]
    log = []
    result = rank(
        papers, Settings(sources=[], max_paper_stories=0), FakeRanker(), prompt, [], audit=log
    )
    assert result == []
    assert sum(r["status"] == "paper_cap" for r in log) == 2


def test_x_evidence_is_never_refetched_by_article_hydration(monkeypatch):
    def forbidden(*args):
        pytest.fail("X evidence must come only from the bounded gateway/cache")

    monkeypatch.setattr("ai_dash.content.read_article", forbidden)
    original = item(url="https://x.com/test/status/123", text="An original short post.")
    result, log = hydrate([original], Settings(sources=[]))
    assert result == [original] and log == []
