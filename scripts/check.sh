#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
uv sync --frozen --no-editable --reinstall-package ai-dash
uv run --no-sync ruff check .
uv run --no-sync ruff format --check .
uv run --no-sync pytest -q
uv run --no-sync ai-dash validate
uv run --no-sync python scripts/render-windmill.py --check
uv build
