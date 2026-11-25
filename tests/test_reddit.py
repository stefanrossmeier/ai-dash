from datetime import UTC, datetime, timedelta

import httpx
import pytest

from ai_dash.models import Settings, Source
from ai_dash.reddit import retrieve_reddit
from ai_dash.retrieval import retrieve_one

NOW = datetime(2026, 11, 25, 16, tzinfo=UTC)


@pytest.fixture
def credentials(tmp_path, monkeypatch):
    for name, value in [
        ("reddit_client_id", "fixture-client"),
        ("reddit_client_secret", "fixture-secret"),
        ("reddit_user_agent", "script:ai-dash:test (by /u/fixture)"),
    ]:
        p = tmp_path / name
        p.write_text(value)
        p.chmod(0o600)
        monkeypatch.setenv(f"AI_DASH_{name.upper()}_FILE", str(p))
    return tmp_path


def source(**kwargs):
    return Source(
        id="singularity",
        name="r/singularity",
        category="Community",
        priority="P1",
        kind="reddit",
        url="https://www.reddit.com/r/singularity/",
        endpoint="https://oauth.reddit.com/r/singularity/new",
        focus="AI",
        **kwargs,
    )


def post(key, age=1, **kwargs):
    return {
        "kind": "t3",
        "data": {
            "title": f"Major AI capability {key}",
            "permalink": f"/r/singularity/comments/{key}/test/",
            "created_utc": (NOW - timedelta(hours=age)).timestamp(),
            "selftext": "Primary announcement and supporting evidence.",
            "url": "https://publisher.example/release",
            **kwargs,
        },
    }


def install_transport(monkeypatch, handler):
    original = httpx.Client
    monkeypatch.setattr(
        "ai_dash.reddit.httpx.Client",
        lambda **kw: original(transport=httpx.MockTransport(handler), **kw),
    )


def test_oauth_paginates_and_filters_window_without_exposing_tokens(credentials, monkeypatch):
    seen = []

    def handler(request):
        seen.append(request)
        if request.url.path == "/api/v1/access_token":
            assert request.url.host == "www.reddit.com"
            assert request.headers["Authorization"].startswith("Basic ")
            assert b"client_credentials" in request.content
            return httpx.Response(200, json={"access_token": "fixture-access-token"})
        assert request.url.host == "oauth.reddit.com"
        assert request.headers["Authorization"] == "Bearer fixture-access-token"
        assert "ai-dash" in request.headers["User-Agent"]
        if not request.url.params.get("after"):
            return httpx.Response(200, json={"data": {"children": [post("a")], "after": "t3_a"}})
        assert request.url.params["after"] == "t3_a"
        return httpx.Response(
            200,
            json={
                "data": {
                    "children": [
                        post("a"),
                        post("boundary", age=12),
                        post("old", age=13),
                        post("future", age=-1),
                        post("sticky", stickied=True),
                    ],
                    "after": "t3_old",
                }
            },
        )

    install_transport(monkeypatch, handler)
    items, coverage = retrieve_one(source(), Settings(sources=[], freshness_hours=12), NOW)
    assert len(seen) == 3
    assert len(items) == coverage.items == coverage.fresh == 2
    assert coverage.status == "ok"
    assert all(i.date_basis == "submission" for i in items)
    assert all(NOW - timedelta(hours=12) <= i.published_at < NOW for i in items)
    assert "fixture-secret" not in str(items) + str(coverage)
    assert "fixture-access-token" not in str(items) + str(coverage)


@pytest.mark.parametrize("status", [401, 403, 429])
def test_upstream_errors_are_visible_without_raw_provider_text(credentials, monkeypatch, status):
    install_transport(
        monkeypatch,
        lambda request: httpx.Response(
            status, json={"error": "fixture-secret raw-private-provider-error"}
        ),
    )
    items, coverage = retrieve_reddit(source(), Settings(sources=[]), NOW)
    assert items == [] and coverage.status == "unavailable"
    assert coverage.detail == f"reddit_oauth_http_{status}"
    assert "fixture-secret" not in str(coverage)


def test_broad_secret_permissions_are_rejected_without_network(credentials, monkeypatch):
    (credentials / "reddit_client_secret").chmod(0o644)
    monkeypatch.setattr("ai_dash.reddit.httpx.Client", lambda **kw: pytest.fail("HTTP called"))
    items, coverage = retrieve_reddit(source(), Settings(sources=[]), NOW)
    assert items == [] and coverage.detail == "reddit_credentials_unavailable"


def test_redirects_never_forward_credentials(credentials, monkeypatch):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(302, headers={"Location": "https://untrusted.example/"})

    install_transport(monkeypatch, handler)
    items, coverage = retrieve_reddit(source(), Settings(sources=[]), NOW)
    assert items == [] and len(calls) == 1
    assert coverage.detail == "reddit_oauth_http_302"


def test_empty_listing_is_healthy_empty_not_unavailable(credentials, monkeypatch):
    def handler(request):
        payload = (
            {"access_token": "token"}
            if request.method == "POST"
            else {"data": {"children": [], "after": None}}
        )
        return httpx.Response(200, json=payload)

    install_transport(monkeypatch, handler)
    items, coverage = retrieve_reddit(source(), Settings(sources=[]), NOW)
    assert items == [] and coverage.status == "empty"
