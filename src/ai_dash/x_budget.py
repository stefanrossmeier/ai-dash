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


class XDailyBudget:
    """Reserve paid X retrieval against a daily cost cap.

    Each request reserves room under the day's limit before it runs; the
    reservation is provisional (an estimate), and `record_cost` writes the
    actual provider-reported cost afterwards. The day's cache still serves
    identical-handle requests for free; a different watchlist in the same
    day pays for a fresh request while budget remains.
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
            "SELECT COALESCE(SUM(cost_usd), 0) FROM requests WHERE day = ?", (day,)
        ).fetchall()
        return float(rows[0][0]) if rows else 0.0

    def _reserve(self, day: str) -> float:
        """Reserve one request's headroom under the daily cap; return the spent amount."""
        with sqlite3.connect(self.root / "requests.sqlite") as db:
            db.execute("PRAGMA synchronous=FULL")
            db.execute(
                """CREATE TABLE IF NOT EXISTS requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    day TEXT NOT NULL,
                    handles TEXT NOT NULL,
                    requested_at TEXT NOT NULL,
                    cost_usd REAL NOT NULL DEFAULT 0.0
                )"""
            )
            # Migrate the legacy one-request-per-day schema if present.
            columns = {row[1] for row in db.execute("PRAGMA table_info(requests)")}
            if "cost_usd" not in columns:
                db.execute("ALTER TABLE requests ADD COLUMN cost_usd REAL NOT NULL DEFAULT 0.0")
                db.execute("ALTER TABLE requests ADD COLUMN id INTEGER")
            spent = self._spent(db, day)
            if spent >= DAILY_COST_LIMIT_USD:
                raise RuntimeError(
                    f"daily X retrieval cost limit reached (${spent:.2f} of "
                    f"${DAILY_COST_LIMIT_USD:.2f}); no automatic paid retry"
                )
            db.execute(
                "INSERT INTO requests (day, handles, requested_at, cost_usd) VALUES (?, ?, ?, ?)",
                (
                    day,
                    "reserved",
                    datetime.now(UTC).isoformat(),
                    # Provisional reservation: assume one typical request's cost.
                    0.0,
                ),
            )
            db.commit()
            return spent

    def cached_or_reserve(self, handles: list[str]) -> dict | None:
        if not handles or len(handles) > 7 or len({h.casefold() for h in handles}) != len(handles):
            raise ValueError("X retrieval requires one to seven unique accounts")
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
                "UPDATE requests SET cost_usd = ? WHERE id = "
                "(SELECT MAX(id) FROM requests WHERE day = ?)",
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
