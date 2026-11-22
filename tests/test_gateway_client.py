from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from ai_dash.gateway import Gateway, _idempotency_key


class _Response:
    is_error = False

    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def json(self) -> dict:
        return self._payload


class GatewayHeaderTests(unittest.TestCase):
    def test_identical_requests_reuse_the_idempotency_key(self) -> None:
        """A retry of one logical request must reuse its key, otherwise the
        gateway records and charges it as a brand-new request. A new run (fresh
        process nonce) must get a new key so reruns still execute."""
        payload = {"alias": "rank-cheap", "purpose": "ranking", "profile": "ai-dash"}
        self.assertEqual(_idempotency_key(payload), _idempotency_key(dict(payload)))
        self.assertNotEqual(
            _idempotency_key(payload), _idempotency_key({**payload, "user": "changed"})
        )
        baseline = _idempotency_key(payload)
        with patch("ai_dash.gateway._RUN_NONCE", "second-run"):
            self.assertNotEqual(_idempotency_key(payload), baseline)

    def test_chat_sends_bearer_and_stable_key(self) -> None:
        with TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "gateway.token"
            token_file.write_text("synthetic-token\n", encoding="utf-8")
            with patch.dict(
                "os.environ",
                {
                    "AI_DASH_GATEWAY_TOKEN_FILE": str(token_file),
                },
                clear=False,
            ):
                seen: list[dict] = []

                def fake_post(url: str, *, json: dict, headers: dict | None = None, **kw: object):
                    seen.append({"url": url, "headers": headers or {}})
                    return _Response({"content": {}, "provider_metadata": {"scope_verified": True}})

                with patch("ai_dash.gateway.httpx.post", fake_post):
                    gateway = Gateway("http://ai-dash-llm-gateway:8080")
                    payload = {"alias": "rank-cheap", "purpose": "ranking"}
                    gateway.request("chat", payload)
                    first = seen[-1]["headers"]
                    gateway.request("chat", dict(payload))
                    second = seen[-1]["headers"]

                self.assertEqual(seen[0]["url"], "http://ai-dash-llm-gateway:8080/v1/chat")
                self.assertEqual(first["Authorization"], "Bearer synthetic-token")
                self.assertTrue(first["Idempotency-Key"].startswith("ai-dash:"))
                self.assertEqual(first["Idempotency-Key"], second["Idempotency-Key"])
                with self.assertRaisesRegex(ValueError, "free RSS"):
                    gateway.request("x-search", {})


if __name__ == "__main__":
    unittest.main()
