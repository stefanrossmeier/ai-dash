#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
uv sync --frozen
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
uv run ai-dash validate
uv run python scripts/render-windmill.py --check
uv build
