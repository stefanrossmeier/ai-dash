from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo


class XDailyBudget:
    """Reserve before a paid request: failures/crashes consume the day's single attempt."""

    def __init__(self, root: Path, timezone: str = "Europe/Berlin"):
        self.root = root / "x-budget"
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.timezone = timezone

    def day(self) -> str:
        return datetime.now(UTC).astimezone(ZoneInfo(self.timezone)).date().isoformat()

    def cache_path(self, day: str) -> Path:
        return self.root / f"{day}.json"

    def cached_or_reserve(self, handles: list[str]) -> dict | None:
        if not handles or len(handles) > 7 or len({h.casefold() for h in handles}) != len(handles):
            raise ValueError("X retrieval requires one to seven unique accounts")
        day = self.day()
        self.reserved_day = day
        cache = self.cache_path(day)
        if cache.exists():
            saved = json.loads(cache.read_text())
            if not {h.casefold() for h in handles} <= set(saved["handles"]):
                raise RuntimeError("daily X request already used for a different watchlist")
            result = saved["response"]
            result["cached"] = True
            result["original_usage"] = result.get("usage", {})
            result["usage"] = {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "cost_usd": 0.0,
            }
            result["latency_ms"] = 0
            return result
        with sqlite3.connect(self.root / "requests.sqlite") as db:
            db.execute("PRAGMA synchronous=FULL")
            db.execute("""CREATE TABLE IF NOT EXISTS requests (
                day TEXT PRIMARY KEY, handles TEXT NOT NULL, requested_at TEXT NOT NULL
            )""")
            try:
                db.execute(
                    "INSERT INTO requests VALUES (?, ?, ?)",
                    (
                        day,
                        json.dumps(sorted(h.casefold() for h in handles)),
                        datetime.now(UTC).isoformat(),
                    ),
                )
                db.commit()
            except sqlite3.IntegrityError:
                raise RuntimeError(
                    "daily X retrieval limit reached; no automatic paid retry"
                ) from None
        return None

    def save(self, handles: list[str], response: dict):
        day = getattr(self, "reserved_day", self.day())
        path = self.cache_path(day)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps({"handles": sorted(h.casefold() for h in handles), "response": response})
        )
        temporary.replace(path)
