from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# Maximum total spend on paid X retrieval per day. A typical combined
# watchlist request costs ~$0.06, so this allows the scheduled run plus
# retries and bounded test runs without an unguarded spend path.
DAILY_COST_LIMIT_USD = 0.60

# The cost ledger lives in its own table: a legacy `requests` table with
# day as PRIMARY KEY cannot be migrated in place (sqlite cannot drop a
# PRIMARY KEY), so it is simply abandoned where it exists.
LEDGER_TABLE = "x_requests"


class XDailyBudget:
    """Reserve paid X retrieval against a daily cost cap.

    Each fresh (uncached) request reserves headroom under the day's limit
    before it runs; `record_cost` writes the actual provider-reported cost
    afterwards. The day's cache file serves any request for free.
    """

    def __init__(self, root: Path, timezone: str = "Europe/Berlin") -> None:
        self.root = root / "x-budget"
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.timezone = timezone

    def day(self) -> str:
        return datetime.now(UTC).astimezone(ZoneInfo(self.timezone)).date().isoformat()

    def cache_path(self, day: str) -> Path:
        return self.root / f"{day}.json"

    def _spent(self, db: sqlite3.Connection, day: str) -> float:
        rows = db.execute(
            f"SELECT COALESCE(SUM(cost_usd), 0) FROM {LEDGER_TABLE} WHERE day = ?",  # noqa: S608
            (day,),
        ).fetchall()
        return float(rows[0][0]) if rows else 0.0

    def _reserve(self, day: str) -> float:
        """Reserve one request's headroom under the daily cap; return the spent amount."""
        with sqlite3.connect(self.root / "requests.sqlite") as db:
            db.execute("PRAGMA synchronous=FULL")
            db.execute(
                f"""CREATE TABLE IF NOT EXISTS {LEDGER_TABLE} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    day TEXT NOT NULL,
                    handles TEXT NOT NULL,
                    requested_at TEXT NOT NULL,
                    cost_usd REAL NOT NULL DEFAULT 0.0
                )"""
            )
            spent = self._spent(db, day)
            if spent >= DAILY_COST_LIMIT_USD:
                raise RuntimeError(
                    f"daily X retrieval cost limit reached (${spent:.2f} of "
                    f"${DAILY_COST_LIMIT_USD:.2f}); no automatic paid retry"
                )
            db.execute(
                f"INSERT INTO {LEDGER_TABLE} (day, handles, requested_at, cost_usd) "
                "VALUES (?, ?, ?, ?)",
                (day, "reserved", datetime.now(UTC).isoformat(), 0.0),
            )
            db.commit()
            return spent

    def cached_or_reserve(self, handles: list[str]) -> dict | None:
        if not handles or len(handles) > 14 or len({h.casefold() for h in handles}) != len(handles):
            raise ValueError("X retrieval requires one to fourteen unique accounts")
        day = self.day()
        self.reserved_day = day
        cache = self.cache_path(day)
        if cache.exists():
            saved = json.loads(cache.read_text())
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
        self._reserve(day)
        return None

    def record_cost(self, cost_usd: float, day: str | None = None) -> None:
        """Write the actual provider-reported cost of the latest reservation."""
        effective_day = day or getattr(self, "reserved_day", self.day())
        with sqlite3.connect(self.root / "requests.sqlite") as db:
            db.execute(
                f"UPDATE {LEDGER_TABLE} SET cost_usd = ? WHERE id = "
                f"(SELECT MAX(id) FROM {LEDGER_TABLE} WHERE day = ?)",
                (cost_usd, effective_day),
            )
            db.commit()

    def save(self, handles: list[str], response: dict):
        day = getattr(self, "reserved_day", self.day())
        path = self.cache_path(day)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps({"handles": sorted(h.casefold() for h in handles), "response": response})
        )
        temporary.replace(path)
