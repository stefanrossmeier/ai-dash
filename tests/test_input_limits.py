import json

import httpx
import pytest

from ai_dash.gateway import Gateway, GatewayInputLimitError
from ai_dash.ranking import bounded_chat, keyed_schema


@pytest.mark.parametrize("field", ["evaluations", "summaries"])
def test_limit_rejections_split_recursively_and_process_every_remaining_item(field):
    candidates = [{"id": f"c{n}", "evidence": "facts"} for n in range(7)]
    payload = {
        "messages": [{"role": "user", "content": json.dumps({"candidates": candidates})}],
        "response_schema": keyed_schema(field, [c["id"] for c in candidates], {"type": "string"}),
    }
    original = json.dumps(payload)
    accepted = []

    class Limited:
        def request(self, route, body):
            batch = json.loads(body["messages"][-1]["content"])["candidates"]
            if len(batch) > 2:
                raise GatewayInputLimitError("input_token_limit")
            ids = [c["id"] for c in batch]
            schema = body["response_schema"]["properties"][field]
            assert set(schema["required"]) == set(schema["properties"]) == set(ids)
            accepted.extend(ids)
            return {"content": {field: {key: "result" for key in ids}}}

    result = bounded_chat(Limited(), payload, field)
    assert accepted == [c["id"] for c in candidates]
    assert set(result["content"][field]) == set(accepted)
    assert json.dumps(payload) == original


def test_other_failures_are_never_retried_or_split():
    class UnknownOutcome:
        calls = 0

        def request(self, *args):
            self.calls += 1
            raise RuntimeError("gateway transport lost")

    gateway = UnknownOutcome()
    with pytest.raises(RuntimeError, match="transport lost"):
        bounded_chat(gateway, {}, "evaluations")
    assert gateway.calls == 1


def test_preflight_limit_does_not_register_an_oversized_request(monkeypatch):
    monkeypatch.setenv("AI_DASH_RUN_ID", "test-run")
    monkeypatch.setenv("AI_DASH_GATEWAY_INPUT_LIMIT", "8192")
    gateway = Gateway("http://gateway")
    gateway.token = "synthetic-token"
    monkeypatch.setattr("ai_dash.gateway.httpx.post", lambda *a, **kw: pytest.fail("HTTP called"))
    with pytest.raises(GatewayInputLimitError, match="preflight"):
        gateway.request("chat", {"messages": [{"content": "x" * 9000}]})


def test_single_oversized_candidate_fails_without_looping_or_silent_loss():
    class Limited:
        def request(self, *args):
            raise GatewayInputLimitError("input_size_limit")

    with pytest.raises(GatewayInputLimitError):
        bounded_chat(
            Limited(), {"messages": [{"content": '{"candidates":[{"id":"c0"}]}'}]}, "evaluations"
        )


@pytest.mark.parametrize(
    "code", ["input_token_limit", "input_size_limit", "request_schema_invalid"]
)
def test_client_splits_only_known_input_limits_and_does_not_echo_raw_error(monkeypatch, code):
    monkeypatch.setenv("AI_DASH_RUN_ID", "test-run")
    gateway = Gateway("http://gateway")
    gateway.token = "synthetic-token"
    monkeypatch.setattr(
        "ai_dash.gateway.httpx.post",
        lambda *a, **kw: httpx.Response(
            422, json={"error": {"code": code, "message": "private upstream text"}}
        ),
    )
    expected = GatewayInputLimitError if code != "request_schema_invalid" else RuntimeError
    with pytest.raises(expected) as caught:
        gateway.request("chat", {})
    assert "private upstream text" not in str(caught.value)
    if code == "request_schema_invalid":
        assert not isinstance(caught.value, GatewayInputLimitError)
