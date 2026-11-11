from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from ai_dash.delivery import Telegram
from ai_dash.gateway import Gateway
from ai_dash.models import load_settings
from ai_dash.pipeline import build, run
from ai_dash.presentation import render
from ai_dash.reports import load_reports, select_report
from ai_dash.retrieval import collect
from ai_dash.storage import Store, exclusive


def secret(name: str) -> str:
    path = os.getenv(name + "_FILE")
    value = Path(path).read_text().strip() if path else os.getenv(name, "").strip()
    if not value:
        raise ValueError(name + " or " + name + "_FILE is required")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description="AI engineering news on independent Windmill infrastructure"
    )
    parser.add_argument(
        "command",
        choices=[
            "validate",
            "collect",
            "preview",
            "run",
            "status",
            "check-telegram",
            "resolve-delivery",
        ],
    )
    home = Path(os.getenv("AI_DASH_HOME", "."))
    parser.add_argument("--report", help="Report ID from config/reports.yaml")
    parser.add_argument("--reports", type=Path, default=home / "config/reports.yaml")
    parser.add_argument(
        "--example", action="store_true", help="Label and send this report example, even if quiet"
    )
    parser.add_argument("--config", type=Path, default=home / "config/sources.yaml")
    parser.add_argument("--prompt", type=Path, default=home / "assets/editorial.md")
    parser.add_argument(
        "--data-dir", type=Path, default=Path(os.getenv("AI_DASH_DATA_DIR", "./var"))
    )
    parser.add_argument(
        "--gateway-url", default=os.getenv("AI_DASH_GATEWAY_URL", "http://127.0.0.1:18082")
    )
    parser.add_argument(
        "--no-x", action="store_true", help="Skip X with explicit search_required coverage"
    )
    parser.add_argument("--output", type=Path, help="Write collection/preview JSON to this file")
    parser.add_argument("--run-id")
    parser.add_argument("--part", type=int)
    parser.add_argument("--resolution", choices=["sent", "pending"])
    args = parser.parse_args()
    # Network logs can contain Telegram credentials embedded in URL paths.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    try:
        if args.command == "check-telegram":
            result = Telegram(secret("AI_DASH_TELEGRAM_TOKEN")).check(
                secret("AI_DASH_TELEGRAM_CHAT_ID")
            )
        elif args.command in {"status", "resolve-delivery"}:
            with exclusive(args.data_dir):
                store = Store(args.data_dir)
                try:
                    if args.command == "resolve-delivery":
                        if args.run_id is None or args.part is None or args.resolution is None:
                            raise ValueError(
                                "resolution requires --run-id, --part and --resolution"
                            )
                        store.resolve(args.run_id, args.part, args.resolution)
                    result = store.status()
                finally:
                    store.close()
        else:
            settings = load_settings(args.config)
            reports = load_reports(args.reports)
            if args.report:
                settings = select_report(settings, reports, args.report)
            elif args.command != "validate":
                raise ValueError("--report is required; the mixed digest has been retired")
            if args.example:
                settings = settings.model_copy(update={"example": True})
            gateway = Gateway(args.gateway_url, args.data_dir, settings.timezone)
            if args.command == "validate":
                result = {
                    "sources": len(settings.sources),
                    "reports": [
                        {
                            "id": r.id,
                            "title": r.title,
                            "enabled": r.enabled,
                            "slots": r.slots,
                            "sources": len(select_report(settings, reports, r.id).sources),
                        }
                        for r in reports.reports
                    ]
                    if not args.report
                    else settings.report_title,
                    "slots": settings.slots if args.report else [],
                    "timezone": settings.timezone,
                }
            elif args.command == "run":
                result = run(
                    settings,
                    gateway,
                    args.prompt,
                    args.data_dir,
                    Telegram(secret("AI_DASH_TELEGRAM_TOKEN")),
                    secret("AI_DASH_TELEGRAM_CHAT_ID"),
                    no_x=args.no_x,
                )
            elif args.command == "collect":
                items, coverage = collect(settings, gateway, datetime.now(UTC), no_x=args.no_x)
                result = {
                    "items": [i.model_dump(mode="json") for i in items],
                    "coverage": [c.model_dump(mode="json") for c in coverage],
                    "traces": gateway.traces,
                }
            else:
                # Preview has no writes to the state DB or delivery history.
                history = []
                if (args.data_dir / "state.sqlite").exists():
                    with exclusive(args.data_dir):
                        store = Store(args.data_dir)
                        try:
                            history = store.history(datetime.now(UTC), settings.history_days)
                        finally:
                            store.close()
                artifact = build(settings, gateway, args.prompt, history, no_x=args.no_x)
                result = artifact.model_dump(mode="json")
                for message in render(artifact, settings.timezone):
                    print(message, file=sys.stderr)
        payload = json.dumps(result, indent=2, ensure_ascii=False)
        if args.output:
            args.output.write_text(payload + "\n")
            print(json.dumps({"output": str(args.output)}))
        else:
            print(payload)
        return 0
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"ai-dash: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
