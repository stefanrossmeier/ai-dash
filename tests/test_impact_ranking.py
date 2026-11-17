import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from ai_dash.model_gateway import ChatRequest, chat
from ai_dash.models import ImpactDecision, Item, Settings
from ai_dash.processing import rank
from ai_dash.ranking import rejection_reasons, selection_score
from tests.ranking_helpers import FakeImpactRanker


def decision(**updates):
    return ImpactDecision.model_validate(
        {
            "rank_score": 80,
            "impact": 80,
            "breadth": 80,
            "quality": 80,
            "novelty": 80,
            "tier": 4,
            "change_type": "new_capability",
            "event_key": "material-model-launch",
            "reason": "New broad capability supported by release evidence.",
        }
        | updates
    )


@pytest.mark.parametrize(
    "updates,reason",
    [
        ({"change_type": "routine_update", "impact": 100, "breadth": 100}, "routine_update"),
        ({"tier": 2}, "low_tier"),
        (
            {"rank_score": 100, "quality": 100, "novelty": 100, "impact": 35, "breadth": 25},
            "low_impact",
        ),
        ({"impact": 100, "breadth": 30}, "narrow_breadth"),
        ({"novelty": 0}, "low_novelty"),
        ({"quality": 40}, "weak_evidence"),
    ],
)
def test_independent_floors_cannot_be_rescued_by_high_other_scores(updates, reason):
    assert reason in rejection_reasons(decision(**updates), Settings(sources=[]))


def test_joint_impact_breadth_and_material_analysis_boundary():
    assert selection_score(decision(impact=100, breadth=10)) < 50
    analysis = decision(
        impact=65,
        breadth=65,
        rank_score=80,
        novelty=70,
        quality=90,
        tier=3,
        change_type="substantive_analysis",
    )
    assert selection_score(analysis) == 70.25
    assert rejection_reasons(analysis, Settings(sources=[])) == []


def test_critical_security_and_major_cli_capabilities_are_eligible():
    for change in ("material_security", "new_capability"):
        assert rejection_reasons(decision(change_type=change), Settings(sources=[])) == []


def test_large_pool_is_compact_source_neutral_and_only_finalists_get_summaries(tmp_path):
    prompt = tmp_path / "prompt.md"
    prompt.write_text("Rank impact, not routine utility.")
    items = [
        Item(
            id=str(n),
            title=f"Major capability {n}",
            url=f"https://publisher.example/{n}",
            published_at=datetime.now(UTC),
            source_id="source",
            source="Publisher",
            category="Lab",
            priority="P1",
            text="Documented capability and impact. " * 300,
        )
        for n in range(372)
    ]
    gateway = FakeImpactRanker()
    stories = rank(items, Settings(sources=[], max_stories=5), gateway, prompt, [])
    scoring = [
        json.loads(c["messages"][1]["content"])["candidates"]
        for c in gateway.calls
        if c["purpose"] == "ai-news-ranking"
    ]
    assert list(map(len, scoring)) == [150, 150, 72]
    assert sum(map(len, scoring)) == 372
    for batch in scoring:
        for candidate in batch:
            assert set(candidate) == {"id", "headline", "evidence", "date_basis"}
            assert len(candidate["evidence"]) <= 1200
    summaries = [
        json.loads(c["messages"][1]["content"])["candidates"]
        for c in gateway.calls
        if c["purpose"] == "ai-news-summaries"
    ]
    assert len(stories) == 5 and len(summaries) == 1 and len(summaries[0]) == 5


def test_rejected_pool_has_no_consolidation_or_summary_cost(tmp_path):
    prompt = tmp_path / "prompt.md"
    prompt.write_text("Rank impact.")
    item = Item(
        id="a",
        title="Minor UI patch",
        url="https://example.org/a",
        published_at=datetime.now(UTC),
        source_id="s",
        source="S",
        category="GitHub",
        priority="P1",
        text="A minor UI change. " * 20,
    )
    gateway = FakeImpactRanker(score=35)
    assert rank([item], Settings(sources=[]), gateway, prompt, []) == []
    assert [c["purpose"] for c in gateway.calls] == ["ai-news-ranking"]


def test_shortlist_summary_validation_cannot_add_or_omit_items(tmp_path):
    prompt = tmp_path / "prompt.md"
    prompt.write_text("Rank impact.")
    item = Item(
        id="a",
        title="Major new model",
        url="https://example.org/a",
        published_at=datetime.now(UTC),
        source_id="s",
        source="S",
        category="Lab",
        priority="P1",
        text="Important capability. " * 20,
    )

    class BadSummary(FakeImpactRanker):
        def request(self, route, body):
            if body["purpose"] == "ai-news-summaries":
                return {"content": {"summaries": {"invented": "Wrong story"}}}
            return super().request(route, body)

    with pytest.raises(ValueError, match="summaries omitted"):
        rank([item], Settings(sources=[]), BadSummary(), prompt, [])


def test_owned_gateway_forwards_low_reasoning_and_output_budget():
    provider = AsyncMock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "{}"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            },
        )
    )
    config = {
        "aliases": {
            "rank-cheap": {
                "provider": "openrouter",
                "model": "openai/gpt-6-luna",
                "max_attempts": 1,
                "reasoning_effort": "low",
                "max_output_tokens": 32768,
            }
        }
    }
    with (
        patch("ai_dash.model_gateway._load_config", return_value=config),
        patch("ai_dash.model_gateway._load_api_key", return_value="test"),
        patch("ai_dash.model_gateway._post_openrouter", provider),
    ):
        result = asyncio.run(chat(ChatRequest(alias="rank-cheap", purpose="test", messages=[])))
    payload = provider.call_args.kwargs["payload"]
    assert payload["model"] == "openai/gpt-6-luna"
    assert payload["reasoning"] == {"effort": "low", "exclude": True}
    assert payload["max_tokens"] == 32768
    assert result.provider_metadata["reasoning_effort"] == "low"


def test_model_and_threshold_config_are_independent_and_explicit():
    import yaml

    root = Path(__file__).resolve().parents[1]
    source = yaml.safe_load((root / "config/sources.yaml").read_text())
    model = yaml.safe_load((root / "config/model-gateway.yaml").read_text())["aliases"][
        "rank-cheap"
    ]
    assert source["min_score"] == 65 and source["ranking_batch_size"] == 150
    assert model["model"] == "openai/gpt-6-luna" and model["reasoning_effort"] == "low"
    from ai_dash.models import load_settings
    from ai_dash.reports import load_reports, select_report

    base = load_settings(root / "config/sources.yaml")
    reports = load_reports(root / "config/reports.yaml")
    assert select_report(base, reports, "research_oss").min_score == 60
    assert select_report(base, reports, "company").min_score == 65
    assert select_report(base, reports, "x_major").min_score == 25
