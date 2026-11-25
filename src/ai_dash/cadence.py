"""Use the preceding scheduled interval plus a small overlap for fresh reports."""

import math
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo


def freshness_for_slots(slots: list[str], timezone: str, now: datetime | None = None) -> int:
    if not slots:
        raise ValueError("report needs at least one daily slot")
    now = now or datetime.now(UTC)
    if now.tzinfo is None:
        raise ValueError("report time must be timezone-aware")
    zone = ZoneInfo(timezone)
    today = now.astimezone(zone).date()
    scheduled = sorted(
        {
            datetime.fromisoformat(f"{today - timedelta(days=days)}T{slot}")
            .replace(tzinfo=zone)
            .astimezone(UTC)
            for days in range(3)
            for slot in slots
        }
    )
    past = [at for at in scheduled if at <= now]
    interval = (past[-1] - past[-2]).total_seconds() / 3600
    overlap = 1 if len(set(slots)) == 1 else 2
    return math.ceil(interval + overlap)
