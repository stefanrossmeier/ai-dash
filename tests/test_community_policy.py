from datetime import UTC, datetime
from pathlib import Path

import pytest

from ai_dash.content import hydrate
from ai_dash.models import ImpactDecision, Item, Settings, Story, load_settings
from ai_dash.ranking import rejection_reasons, summarize
from ai_dash.reports import load_reports, select_report

ROOT = Path(__file__).resolve().parents[1]


def community_settings():
    return select_report(
        load_settings(ROOT / "config/sources.yaml"),
        load_reports(ROOT / "config/reports.yaml"),
        "singularity",
    )


def decision(**kwargs):
    return ImpactDecision(
        **{
            "rank_score": 65,
            "impact": 50,
            "breadth": 55,
            "novelty": 60,
            "quality": 45,
            "tier": 2,
            "change_type": "other",
            "event_key": "reported-ai-research-claim",
            "reason": "Concrete, interesting reported claim; independent validation not supplied.",
            **kwargs,
        }
    )


def post(**kwargs):
    return Item(
        **{
            "id": "discussion",
            "title": "Community discusses a reported AI research result",
            "url": "https://reddit.com/r/singularity/comments/abc/discussion",
            "published_at": datetime(2026, 11, 25, 10, tzinfo=UTC),
            "source_id": "community-r-singularity",
            "source": "r/singularity",
            "category": "Community",
            "priority": "P1",
            "date_basis": "submission",
            "text": "A community submission reports an unverified research result. " * 12,
            **kwargs,
        }
    )


def test_interesting_community_claim_is_not_subject_to_blog_confirmation_floors():
    settings = community_settings()
    assert settings.ranking_prompt == "reddit-editorial.md"
    assert rejection_reasons(decision(), settings) == []
    assert "low_tier" in rejection_reasons(decision(), Settings(sources=[]))
    assert settings.min_score >= 40  # meaningful admission, no filler quota


@pytest.mark.parametrize(
    "change,reason",
    [
        ({"tier": 1}, "low_tier"),
        ({"quality": 5}, "weak_evidence"),
        ({"novelty": 5}, "low_novelty"),
        ({"change_type": "routine_update"}, "routine_update"),
    ],
)
def test_noise_and_repetition_still_fail_the_community_policy(change, reason):
    assert reason in rejection_reasons(decision(**change), community_settings())


def test_linked_article_hydration_preserves_reddit_identity_and_submission_date(monkeypatch):
    article = "https://publisher.example/research"
    original = post(linked_url=article)
    calls = []

    def read(client, url):
        calls.append(url)
        return (
            '<meta property="article:published_time" content="2026-11-24T09:00:00Z">'
            "<article>Primary evidence with methodology and stated limitations. "
            + "The result is a reported experiment, not independently reproduced. " * 30
            + "</article>"
        )

    monkeypatch.setattr("ai_dash.content.read_article", read)
    items, log = hydrate([original], Settings(sources=[]))
    assert calls == [article] and log[0]["status"] == "hydrated"
    result = items[0]
    assert result.id == original.id and result.url == original.url
    assert result.date_basis == "submission" and result.published_at == original.published_at
    assert result.original_published_at == datetime(2026, 11, 24, 9, tzinfo=UTC)
    assert "methodology and stated limitations" in result.text


def test_native_discussion_uses_oauth_text_instead_of_scraping_reddit(monkeypatch):
    original = post(text="A substantive community argument in its original short form.")
    monkeypatch.setattr(
        "ai_dash.content.read_article", lambda *a: pytest.fail("must not scrape discussion")
    )
    items, log = hydrate([original], Settings(sources=[]))
    assert items == [original] and log == []


def test_summary_instructions_preserve_uncertainty_for_reported_claims():
    class Gateway:
        def request(self, route, payload):
            instructions = payload["messages"][0]["content"]
            assert "distinguish what a post claims" in instructions
            assert "Do not turn a purported proof" in instructions
            return {"content": {"summaries": {"s0": "A post reports an unverified result."}}}

    result = summarize([Story(item=post(), score=55, summary="")], community_settings(), Gateway())
    assert "unverified" in result[0].summary
