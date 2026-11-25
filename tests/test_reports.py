from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ai_dash.gateway import Gateway
from ai_dash.models import Artifact, load_settings
from ai_dash.presentation import render
from ai_dash.reports import load_reports, select_report

ROOT = Path(__file__).resolve().parents[1]


def test_reports_use_disjoint_sources_and_fourteen_high_frequency_x_accounts():
    settings = load_settings(ROOT / "config/sources.yaml")
    reports = load_reports(ROOT / "config/reports.yaml")
    groups = {r.id: select_report(settings, reports, r.id) for r in reports.reports}
    # The ten X watchlist accounts are enabled for the daily X report only;
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
        "x-news-clement-delangue",
        "x-news-andrew-ng",
        "x-news-rowan-cheung",
        "x-news-heybarsee",
        "x-news-kimmonismus",
        "x-news-bindu-reddy",
        "x-news-linus-ekenstam",
    }
    # The X report re-delivers still-relevant stories and lets the composite
    # score decide on routine-labelled items; company keeps both gates.
    assert groups["x_major"].omit_delivered is False
    assert groups["company"].omit_delivered is True
    assert groups["x_major"].reject_routine_updates is False
    assert groups["company"].reject_routine_updates is True
    sets = [{s.id for s in g.sources} for g in groups.values()]
    for i, left in enumerate(sets):
        for right in sets[i + 1 :]:
            assert not left & right
    for key in ["company", "blogs", "research_oss", "singularity", "ai_news"]:
        assert not groups[key].x_enabled
        assert all(s.kind != "x" for s in groups[key].sources)
    x = groups["x_major"]
    assert x.x_enabled and len(x.sources) == 14
    assert {s.id for s in x.sources} == enabled_x
    assert x.slots == ["07:45", "11:45", "19:45"] and x.max_per_source == 25
    # Full timelines via free Nitter RSS + a dedicated X-calibrated ranking prompt.
    assert x.ranking_prompt == "x-editorial.md"
    youtube = groups["youtube"]
    assert youtube.no_llm and youtube.freshness_hours == 24
    assert youtube.slots == ["19:30"] and youtube.send_empty
    assert [source.id for source in youtube.sources] == ["youtube-channels"]


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
    assert "No new qualifying stories" in messages[0]


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
