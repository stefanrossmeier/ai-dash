from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from ai_dash.gateway import Gateway
from ai_dash.models import Artifact, load_settings
from ai_dash.presentation import render
from ai_dash.reports import load_reports, select_report
from ai_dash.x_budget import XDailyBudget

ROOT = Path(__file__).resolve().parents[1]


def test_reports_use_disjoint_sources_and_seven_complementary_x_accounts():
    settings = load_settings(ROOT / "config/sources.yaml")
    reports = load_reports(ROOT / "config/reports.yaml")
    groups = {r.id: select_report(settings, reports, r.id) for r in reports.reports}
    # The seven X watchlist accounts are enabled for the daily X report only;
    # every other X source stays disabled so paid retrieval stays bounded.
    assert settings.x_enabled is False
    enabled_x = {s.id for s in settings.sources if s.kind == "x" and s.enabled}
    # High-frequency AI news spreaders: the watchlist is optimized for posting
    # volume and news coverage; quiet-but-prestigious accounts stay disabled.
    assert enabled_x == {
        "x-analyst-swyx-shawn-wang",
        "x-analyst-nathan-lambert",
        "x-analyst-simon-willison",
        "x-news-akhaliq",
        "x-news-reach-vb",
        "x-news-min-choi",
        "x-news-the-ai-grid",
    }
    sets = [{s.id for s in g.sources} for g in groups.values()]
    for i, left in enumerate(sets):
        for right in sets[i + 1 :]:
            assert not left & right
    for key in ["company", "blogs", "research_oss", "singularity", "ai_news"]:
        assert not groups[key].x_enabled
        assert all(s.kind != "x" for s in groups[key].sources)
    x = groups["x_major"]
    assert x.x_enabled and len(x.sources) == 7
    assert {s.id for s in x.sources} == enabled_x
    assert len(x.slots) == 1 and x.max_per_source == 3 and not x.x_retry_split


def test_x_daily_budget_allows_multiple_requests_under_cost_cap(tmp_path, monkeypatch):
    import ai_dash.x_budget as xb

    monkeypatch.setattr(XDailyBudget, "day", lambda _: "2026-11-09")
    budget = XDailyBudget(tmp_path)
    # Several paid requests fit while the day's recorded spend is under the cap.
    for _n in range(3):
        assert budget.cached_or_reserve(["OpenAI"]) is None
        budget.record_cost(0.10)
    assert xb.DAILY_COST_LIMIT_USD == 0.60
    # Once recorded spend reaches the cap, further paid requests are refused.
    assert budget.cached_or_reserve(["OpenAI"]) is None
    budget.record_cost(0.30)
    with pytest.raises(RuntimeError, match="cost limit reached"):
        XDailyBudget(tmp_path).cached_or_reserve(["OpenAI"])
    # A new day resets the cap.
    monkeypatch.setattr(XDailyBudget, "day", lambda _: "2026-11-10")
    assert XDailyBudget(tmp_path).cached_or_reserve(["OpenAI"]) is None


def test_x_cache_reuses_results_with_zero_new_usage(tmp_path):
    budget = XDailyBudget(tmp_path)
    assert budget.cached_or_reserve(["OpenAI", "AnthropicAI"]) is None
    budget.save(
        ["OpenAI", "AnthropicAI"],
        {"content": {"posts": []}, "usage": {"cost_usd": 0.12}, "latency_ms": 700},
    )
    result = XDailyBudget(tmp_path).cached_or_reserve(["openai"])
    assert result["cached"] and result["usage"]["cost_usd"] == 0
    assert result["original_usage"]["cost_usd"] == 0.12
    # Any same-day request is served free from the cache; the cost cap only
    # guards fresh paid requests after the cache is absent.
    served = XDailyBudget(tmp_path).cached_or_reserve(["unwatched"])
    assert served is not None and served["cached"]


def test_x_gateway_transport_error_leaves_budget_available_for_retry(tmp_path, monkeypatch):
    calls = []

    def fail(*a, **kw):
        calls.append(kw)
        raise httpx.ReadTimeout("timeout")

    monkeypatch.setattr("ai_dash.gateway.httpx.post", fail)
    for _ in range(2):
        with pytest.raises(RuntimeError):
            Gateway("http://gateway", tmp_path).request(
                "x-search", {"allowed_x_handles": ["OpenAI"]}
            )
    # A transport failure costs nothing, so the retry reaches the gateway
    # again instead of being blocked by a consumed one-shot daily attempt.
    assert len(calls) == 2


def test_large_x_watchlists_fail_before_transport(tmp_path, monkeypatch):
    def fail(*a, **kw):
        pytest.fail("No network request allowed")

    monkeypatch.setattr("ai_dash.gateway.httpx.post", fail)
    with pytest.raises(ValueError):
        Gateway("http://gateway", tmp_path).request(
            "x-search", {"allowed_x_handles": [f"account{i}" for i in range(8)]}
        )


def test_report_examples_are_labelled_and_can_show_quiet_source_groups():
    now = datetime.now(UTC)
    a = Artifact(
        run_id="example",
        created_at=now,
        window_start=now - timedelta(hours=24),
        window_end=now,
        stories=[],
        candidates=[],
        coverage=[],
        traces=[],
        stats={},
        report_id="blogs",
        report_title="Blogs & Analysis",
        example=True,
    )
    messages = render(a, "Europe/Berlin")
    assert len(messages) == 1 and "Blogs & Analysis" in messages[0] and "Example" in messages[0]
    assert "Already-delivered" in messages[0]


def test_daily_x_delivery_is_limited_even_when_report_has_no_stories(tmp_path, monkeypatch):
    from ai_dash.storage import Store

    now = datetime.now(UTC)
    a = Artifact(
        run_id="quiet",
        created_at=now,
        window_start=now - timedelta(hours=24),
        window_end=now,
        stories=[],
        candidates=[],
        coverage=[],
        traces=[],
        stats={},
        report_id="x_major",
        report_title="X",
        send_empty=True,
    )
    store = Store(tmp_path)
    store.persist(a, ["No updates"], "@ai")
    assert not store.delivered_report_today("x_major", now, "Europe/Berlin")
    store.mark("quiet", 0, "sent", 1)
    assert store.delivered_report_today("x_major", now, "Europe/Berlin")
    assert not store.delivered_report_today("blogs", now, "Europe/Berlin")
    assert not store.delivered_report_today("x_major", now + timedelta(days=1), "Europe/Berlin")
    store.close()


def test_empty_successful_x_search_is_quiet_report_not_outage(monkeypatch, tmp_path):
    from ai_dash.models import Coverage, Settings
    from ai_dash.pipeline import build

    monkeypatch.setattr(
        "ai_dash.pipeline.collect",
        lambda *a, **kw: ([], [Coverage(source_id="lab", status="empty")]),
    )
    monkeypatch.setattr("ai_dash.pipeline.rank", lambda *a, **kw: [])
    a = build(
        Settings(sources=[], x_enabled=True, report_id="x_major", send_empty=True),
        Gateway("http://unused"),
        tmp_path / "unused",
        [],
    )
    assert not a.stories and len(render(a, "Europe/Berlin")) == 1


def test_windmill_bash_arguments_use_parseable_positional_assignments():
    import yaml

    folder = ROOT / "workflows/windmill/f/ai_dash"
    shell = (folder / "run_digest.sh").read_text()
    assert '\nreport="$1"\n' in shell and '\nexample="$2"\n' in shell
    for definition in folder.glob("*__flow/flow.yaml"):
        flow = yaml.safe_load(definition.read_text())
        transforms = flow["value"]["modules"][0]["value"]["input_transforms"]
        assert set(transforms) == {"report", "example"}
        assert transforms["example"]["expr"] == "String(flow_input.example ?? false)"


def test_newsroom_feature_outside_news_path_keeps_publisher_date():
    from ai_dash.models import Source
    from ai_dash.retrieval import html_items

    source = Source(
        id="lab",
        name="Lab",
        category="Lab",
        url="https://www.example.org/news",
        endpoint="https://www.example.org/news",
        priority="P1",
        kind="html",
        focus="Models",
    )

    class NoFetch:
        def get(self, *a, **kw):
            pytest.fail("Dated feature should not require guessed URL paths or another fetch")

    page = """<article><header><a href="/news/announcements">Announcements</a>
    <time>Nov 9, 2026</time></header><a href="https://example.org/new-model">
    <h2>Introducing a new frontier model</h2><p>Improved coding and reasoning.</p></a></article>"""
    items, _ = html_items(source, NoFetch(), page, 25)
    assert len(items) == 1
    assert items[0].url == "https://example.org/new-model"
    assert items[0].published_at == datetime(2026, 11, 9, tzinfo=UTC)


def test_explicit_report_pause_is_honored_on_registration():
    import runpy

    reports = load_reports(ROOT / "config/reports.yaml")
    x = next(r for r in reports.reports if r.id == "x_major")
    company = next(r for r in reports.reports if r.id == "company")
    assert x.enabled and company.enabled
    x = x.model_copy(update={"enabled": False})
    policy = runpy.run_path(str(ROOT / "scripts/register-windmill.py"))["should_enable"]
    assert not policy(x.model_dump(), True, [])
    assert not policy(x.model_dump(), False, ["x_major"])
    assert policy(company.model_dump(), True, [])
    assert policy(company.model_dump(), False, ["company"])
    assert not policy(company.model_dump(), False, [])
