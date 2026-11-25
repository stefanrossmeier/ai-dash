from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping
from pathlib import Path

import httpx


class GatewayInputLimitError(RuntimeError):
    """An explicit gateway rejection before provider dispatch; safe to split."""


def _gateway_token() -> str | None:
    """Bearer token for the dedicated llm-gateway instance. Read from a private
    file (AI_DASH_GATEWAY_TOKEN_FILE) or the environment; never logged."""
    path = os.getenv("AI_DASH_GATEWAY_TOKEN_FILE")
    if path:
        return Path(path).read_text(encoding="utf-8").strip()
    value = os.getenv("AI_DASH_GATEWAY_TOKEN", "").strip()
    return value or None


def _run_id() -> str:
    value = next(
        (
            os.environ[k]
            for k in ("AI_DASH_RUN_ID", "WM_ROOT_FLOW_JOB_ID", "WM_JOB_ID")
            if os.getenv(k)
        ),
        None,
    )
    if not value:
        raise RuntimeError("Set AI_DASH_RUN_ID; reuse that ID when recovering an interrupted run")
    return value


def _idempotency_key(payload: Mapping[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return "ai-dash:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class Gateway:
    """Client for ai-dash's independently deployed LLM gateway."""

    def __init__(self, url: str, data_dir: Path | None = None, timezone: str = "Europe/Berlin"):
        self.url = url.rstrip("/")
        self.token = _gateway_token()
        self.traces: list[dict] = []
        # Match the owned gateway's conservative UTF-8 bound, with framing room.
        self.input_limit_bytes = int(os.getenv("AI_DASH_GATEWAY_INPUT_LIMIT", "262144"))
        if self.input_limit_bytes < 4096:
            raise ValueError("AI_DASH_GATEWAY_INPUT_LIMIT must be at least 4096")

    def _headers(self, route: str, payload: dict[str, object]) -> dict[str, str]:
        if not self.token:
            raise RuntimeError("AI_DASH_GATEWAY_TOKEN_FILE or AI_DASH_GATEWAY_TOKEN is required")
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
        payload = {**payload, "run_id": _run_id()}
        size = len(json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode())
        if size + 4096 > self.input_limit_bytes:
            raise GatewayInputLimitError("gateway input preflight limit")
        headers = self._headers(route, payload)
        try:
            response = httpx.post(
                f"{self.url}/v1/{route}",
                json=payload,
                headers=headers,
                timeout=600,
            )
        except httpx.HTTPError:
            identifier = headers["Idempotency-Key"]
            try:
                response = httpx.get(
                    f"{self.url}/v1/requests/{identifier}?format=dashboard",
                    headers=headers,
                    timeout=10,
                )
            except httpx.HTTPError:
                raise RuntimeError(
                    f"gateway transport lost; recover request {identifier}"
                ) from None
        if response.is_error or response.status_code == 202:
            if response.status_code in {413, 422}:
                try:
                    error = response.json().get("error")
                    code = error.get("code") if isinstance(error, dict) else error
                except (ValueError, AttributeError):
                    code = None
                if isinstance(code, str) and code in {
                    "input_token_limit",
                    "input_size_limit",
                    "request_body_too_large",
                }:
                    raise GatewayInputLimitError(
                        f"gateway input limit ({code}); request {headers['Idempotency-Key']}"
                    )
            raise RuntimeError(
                f"gateway HTTP {response.status_code}; request {headers['Idempotency-Key']}"
            )
        result = response.json()
        self.traces.append({k: v for k, v in result.items() if k != "content"})
        if not isinstance(result.get("content"), dict):
            raise ValueError("gateway content must be an object")
        return result
