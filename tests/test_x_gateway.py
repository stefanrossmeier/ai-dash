import copy
import json
from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient

from ai_dash import x_gateway as xg
from ai_dash.gateway import Gateway
from ai_dash.models import Settings, Source
from ai_dash.retrieval import retrieve_x

HANDLES = ["karpathy", "ArtificialAnlys", "fchollet"]
QUERY = "(from:karpathy OR from:ArtificialAnlys OR from:fchollet) since:2026-11-08 until:2026-11-10"
URL = "https://x.com/karpathy/status/2119578471559213411"


def request():
    return xg.SearchRequest(
        alias="x-retrieve",
        purpose="ai-news-retrieval",
        profile="ai-dash",
        input="Original technical posts only",
        allowed_x_handles=HANDLES,
        from_date=date(2026, 11, 8),
        to_date=date(2026, 11, 10),
        response_schema_name="posts",
        response_schema={},
    )


def response(posts=None):
    return {
        "id": "test-generation",
        "model": "x-ai/grok-4.3",
        "status": "completed",
        "output": [
            {"type": "web_search_call", "action": {"query": QUERY}},
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": json.dumps(
                            {
                                "posts": posts
                                if posts is not None
                                else [
                                    dict(
                                        author_handle="karpathy",
                                        post_url=URL,
                                        post_text="A new technical development.",
                                    )
                                ]
                            }
                        ),
                        "annotations": [{"type": "url_citation", "url": URL}],
                    }
                ],
            },
        ],
        "usage": {"input_tokens": 100, "output_tokens": 80, "total_tokens": 180, "cost": 0.01},
    }


def test_request_bounds_search_and_names_actual_accounts_and_exclusive_dates():
    payload = xg.provider_payload(request())
    assert payload["max_tool_calls"] == 1
    assert payload["max_output_tokens"] == 1200
    assert payload["provider"]["allow_fallbacks"] is False
    assert payload["provider"]["order"] == ["xAI"]
    params = payload["tools"][0]["parameters"]
    assert params["x_search"]["allowed_x_handles"] == HANDLES
    assert params["x_search"]["to_date"] == "2026-11-10"
    assert params["max_total_results"] == 6
    prompt = json.loads(payload["input"][1]["content"])
    assert prompt["only_query"] == QUERY and prompt["accounts"] == HANDLES


def test_valid_cited_response_has_scope_verified():
    content, audit = xg.validate_response(response(), request())
    assert content["posts"][0]["post_url"] == URL
    assert audit["scope_verified"] and audit["search_call_count"] == 1


@pytest.mark.parametrize(
    "kind",
    [
        "extra_searches",
        "wrong_author_query",
        "no_author_query",
        "wrong_date",
        "no_search",
        "no_citation",
        "wrong_post_author",
        "incomplete",
    ],
)
def test_unsafe_provider_responses_fail_instead_of_becoming_quiet_editions(kind):
    body = response()
    if kind == "extra_searches":
        body["output"].insert(0, {"type": "web_search_call", "action": {"query": "from:OpenAI"}})
    elif kind == "wrong_author_query":
        body["output"][0]["action"]["query"] = QUERY.replace("from:fchollet", "from:OpenAI")
    elif kind == "no_author_query":
        body["output"][0]["action"]["query"] = "AI news today"
    elif kind == "wrong_date":
        body["output"][0]["action"]["query"] = QUERY.replace("until:2026-11-10", "until:2026-11-09")
    elif kind == "no_search":
        body["output"].pop(0)
    elif kind == "no_citation":
        body["output"][1]["content"][0]["annotations"] = []
    elif kind == "wrong_post_author":
        body["output"][1]["content"][0]["text"] = json.dumps(
            {
                "posts": [
                    dict(
                        author_handle="OpenAI",
                        post_url="https://x.com/OpenAI/status/1",
                        post_text="Not allowed",
                    )
                ]
            }
        )
    else:
        body["status"] = "incomplete"
    with pytest.raises(ValueError):
        xg.validate_response(body, request())


def test_a_real_empty_search_is_distinguished_from_no_search():
    posts, audit = xg.validate_response(response([]), request())
    assert posts == {"posts": []} and audit["scope_verified"]


def setup_gateway(monkeypatch, tmp_path, body):
    monkeypatch.setenv("AI_DASH_X_PROVIDER_DATA", str(tmp_path))
    monkeypatch.setattr(xg, "configured_handles", lambda: {h.casefold() for h in HANDLES})
    calls = []

    def provider(payload):
        calls.append(payload)
        return copy.deepcopy(body)

    monkeypatch.setattr(xg, "call_openrouter", provider)
    return TestClient(xg.app), calls


def test_service_caches_one_success_and_reuses_without_cost(monkeypatch, tmp_path):
    client, calls = setup_gateway(monkeypatch, tmp_path, response())
    first = client.post("/v1/x-search", json=request().model_dump(mode="json"))
    second = client.post("/v1/x-search", json=request().model_dump(mode="json"))
    assert first.status_code == second.status_code == 200
    assert first.json()["usage"]["cost_usd"] == 0.01
    assert second.json()["cached"] and second.json()["usage"]["cost_usd"] == 0
    assert len(calls) == 1


def test_legacy_eighteen_search_trace_is_quarantined_and_not_retried(monkeypatch, tmp_path):
    body = response([])
    body["output"][:0] = [
        {"type": "web_search_call", "action": {"query": f"from:outside{n}"}} for n in range(17)
    ]
    client, calls = setup_gateway(monkeypatch, tmp_path, body)
    for _ in range(2):
        result = client.post("/v1/x-search", json=request().model_dump(mode="json"))
        assert result.status_code == 502
    # A validation failure costs nothing: the retry reaches the provider again
    # under the cost budget instead of being blocked by a consumed daily attempt.
    assert len(calls) == 2
    assert list(tmp_path.glob("*.response.json"))
    assert list(tmp_path.glob("*.failure.json"))


def test_unconfigured_account_rejected_before_any_provider_call(monkeypatch, tmp_path):
    client, calls = setup_gateway(monkeypatch, tmp_path, response())
    body = request().model_dump(mode="json")
    body["allowed_x_handles"] = ["OpenAI"]
    assert client.post("/v1/x-search", json=body).status_code == 422
    assert not calls


def test_health_endpoint_does_not_contact_provider(monkeypatch, tmp_path):
    client, calls = setup_gateway(monkeypatch, tmp_path, response())
    assert client.get("/health").json()["status"] == "ok"
    assert not calls


def test_current_utc_day_is_included_and_retrieval_never_retries():
    now = datetime(2026, 11, 9, 21, tzinfo=UTC)
    s = Source(
        id="karpathy",
        name="Karpathy",
        category="X",
        url="https://x.com/karpathy",
        endpoint="https://x.com/karpathy",
        focus="AI",
        priority="P1",
        kind="x",
    )
    calls = []

    class Fake:
        def request(self, route, payload):
            calls.append(payload)
            return {"content": {"posts": []}, "provider_metadata": {"citation_urls": []}}

    retrieve_x([s], Settings(sources=[s]), Fake(), now)
    assert len(calls) == 1
    assert calls[0]["to_date"] == "2026-11-10"
    assert "karpathy" in calls[0]["input"] and "2026-11-09T21:00:00+00:00" in calls[0]["input"]
    with pytest.raises(ValueError, match="retries"):
        retrieve_x([s], Settings(sources=[s]), Fake(), now, retry_split=True)
    assert len(calls) == 1


def test_application_routes_x_to_its_own_gateway_and_rejects_unverified_cache(
    monkeypatch, tmp_path
):
    import httpx

    monkeypatch.setenv("AI_DASH_X_GATEWAY_URL", "http://own-x:8080")
    calls = []

    def provider(url, **kw):
        calls.append(url)
        return httpx.Response(
            200,
            json={
                "content": {"posts": []},
                "usage": {"cost_usd": 0.01},
                "provider_metadata": {"scope_verified": True},
            },
        )

    monkeypatch.setattr("ai_dash.gateway.httpx.post", provider)
    gateway = Gateway("http://shared-chat:8080", tmp_path)
    gateway.request("x-search", {"allowed_x_handles": HANDLES})
    assert calls == ["http://own-x:8080/v1/x-search"]
    cached = gateway.x_budget.cache_path(gateway.x_budget.day())
    value = json.loads(cached.read_text())
    value["response"]["provider_metadata"] = {}
    cached.write_text(json.dumps(value))
    with pytest.raises(RuntimeError, match="predates scope validation"):
        gateway.request("x-search", {"allowed_x_handles": HANDLES})
    assert len(calls) == 1


def test_query_with_an_unscoped_or_clause_is_not_accepted():
    body = response()
    body["output"][0]["action"]["query"] = QUERY.replace(") since:", " OR trending) since:")
    with pytest.raises(ValueError, match="broadened"):
        xg.validate_response(body, request())


def test_long_x_posts_keep_full_text_within_the_application_limit():
    long_text = "A substantive long-form X post. " * 80
    body = response([dict(author_handle="karpathy", post_url=URL, post_text=long_text)])
    content, audit = xg.validate_response(body, request())
    assert 700 < len(content["posts"][0]["post_text"]) <= 4000
    assert content["posts"][0]["post_text"] == long_text
    assert audit["scope_verified"]


def test_posts_beyond_the_application_limit_are_rejected():
    body = response([dict(author_handle="karpathy", post_url=URL, post_text="x" * 4001)])
    with pytest.raises(ValueError):
        xg.validate_response(body, request())
