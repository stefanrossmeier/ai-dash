from __future__ import annotations

import hashlib
import json
import os
import uuid
from collections.abc import Mapping
from pathlib import Path

import httpx


def _gateway_token() -> str | None:
    """Bearer token for the dedicated llm-gateway instance. Read from a private
    file (AI_DASH_GATEWAY_TOKEN_FILE) or the environment; never logged."""
    path = os.getenv("AI_DASH_GATEWAY_TOKEN_FILE")
    if path:
        return Path(path).read_text(encoding="utf-8").strip()
    value = os.getenv("AI_DASH_GATEWAY_TOKEN", "").strip()
    return value or None


# One nonce per process (one Windmill job run): retries inside the run share
# it, a later run does not.
_RUN_NONCE = uuid.uuid4().hex[:16]


def _idempotency_key(payload: Mapping[str, object]) -> str:
    """Logical-request ID: stable within one run, distinct for the next run.

    The key is the canonical request content plus a per-process run nonce. A
    retry inside the same run replays the gateway's recorded result instead of
    being charged twice, while a fresh run (an operator rerun, or tomorrow's
    scheduled edition) executes as a new request rather than replaying a
    terminal failure forever.
    """
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"ai-dash:{_RUN_NONCE}:{digest}"


class Gateway:
    """Client for ai-dash's independently deployed LLM gateway."""

    def __init__(self, url: str, data_dir: Path | None = None, timezone: str = "Europe/Berlin"):
        self.url = url.rstrip("/")
        self.token = _gateway_token()
        self.traces: list[dict] = []

    def _headers(self, route: str, payload: dict[str, object]) -> dict[str, str]:
        if self.token is None:
            return {}
        # The llm-gateway compatibility wire authenticates the project principal
        # and recovers requests by a content-derived ID, so a retry of the same
        # logical request replays the recorded result instead of paying twice.
        return {
            "Authorization": f"Bearer {self.token}",
            "Idempotency-Key": _idempotency_key(payload),
        }

    def request(self, route: str, payload: dict) -> dict:
        if route != "chat":
            raise ValueError("Only chat inference is supported; X retrieval uses free RSS")
        try:
            response = httpx.post(
                f"{self.url}/v1/{route}",
                json=payload,
                headers=self._headers(route, payload),
                timeout=600,
            )
        except httpx.HTTPError:
            raise RuntimeError("model gateway transport failure") from None
        if response.is_error:
            raise RuntimeError(f"model gateway returned HTTP {response.status_code}")
        result = response.json()
        self.traces.append({k: v for k, v in result.items() if k != "content"})
        if not isinstance(result.get("content"), dict):
            raise ValueError("gateway content must be an object")
        return result
