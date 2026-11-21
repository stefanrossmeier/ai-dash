from __future__ import annotations

import os
import uuid
from pathlib import Path

import httpx

from ai_dash.x_budget import XDailyBudget


def _gateway_token() -> str | None:
    """Bearer token for the dedicated llm-gateway instance. Read from a private
    file (AI_DASH_GATEWAY_TOKEN_FILE) or the environment; never logged."""
    path = os.getenv("AI_DASH_GATEWAY_TOKEN_FILE")
    if path:
        return Path(path).read_text(encoding="utf-8").strip()
    value = os.getenv("AI_DASH_GATEWAY_TOKEN", "").strip()
    return value or None


class Gateway:
    """Client for ai-dash's independently deployed ranking and bounded X gateways."""

    def __init__(self, url: str, data_dir: Path | None = None, timezone: str = "Europe/Berlin"):
        self.url = url.rstrip("/")
        self.x_url = os.getenv("AI_DASH_X_GATEWAY_URL", "http://127.0.0.1:18081").rstrip("/")
        self.token = _gateway_token()
        self.traces: list[dict] = []
        self.x_budget = XDailyBudget(data_dir, timezone) if data_dir is not None else None

    def _headers(self, route: str) -> dict[str, str]:
        if route == "x-search" or self.token is None:
            return {}
        # The llm-gateway compatibility wire authenticates the project principal
        # and recovers requests by stable logical ID, so retries stay idempotent.
        return {
            "Authorization": f"Bearer {self.token}",
            "Idempotency-Key": f"ai-dash:{uuid.uuid4()}",
        }

    def request(self, route: str, payload: dict) -> dict:
        if route == "x-search":
            if self.x_budget is None:
                raise RuntimeError("X retrieval requires a persistent daily budget directory")
            cached = self.x_budget.cached_or_reserve(payload["allowed_x_handles"])
            if cached is not None:
                if cached.get("provider_metadata", {}).get("scope_verified") is not True:
                    raise RuntimeError("Cached X result predates scope validation; no paid retry")
                self.traces.append({k: v for k, v in cached.items() if k != "content"})
                return cached
        try:
            response = httpx.post(
                f"{self.x_url if route == 'x-search' else self.url}/v1/{route}",
                json=payload,
                headers=self._headers(route),
                timeout=200 if route == "x-search" else 600,
            )
        except httpx.HTTPError:
            raise RuntimeError("model gateway transport failure") from None
        if response.is_error:
            raise RuntimeError(f"model gateway returned HTTP {response.status_code}")
        result = response.json()
        self.traces.append({k: v for k, v in result.items() if k != "content"})
        if not isinstance(result.get("content"), dict):
            raise ValueError("gateway content must be an object")
        if route == "x-search":
            if result.get("provider_metadata", {}).get("scope_verified") is not True:
                raise RuntimeError("X gateway did not verify account scope; result rejected")
            self.x_budget.save(payload["allowed_x_handles"], result)
        return result
