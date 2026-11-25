from datetime import datetime

import pytest

from ai_dash.cadence import freshness_for_slots


@pytest.mark.parametrize(
    "slots,now,expected",
    [
        (["15:30"], "2026-11-25T15:30:00+01:00", 25),
        (["00:00", "08:00", "16:00"], "2026-11-25T08:01:00+01:00", 10),
        (["07:30", "17:30"], "2026-11-25T07:30:00+01:00", 16),
        (["07:30", "17:30"], "2026-11-25T17:30:00+01:00", 12),
        (["07:45", "11:45", "19:45"], "2026-11-25T07:45:00+01:00", 14),
        (["07:45", "11:45", "19:45"], "2026-11-25T11:45:00+01:00", 6),
        (["07:45", "11:45", "19:45"], "2026-11-25T19:45:00+01:00", 10),
        (["07:30"], "2026-10-25T07:30:00+01:00", 26),
        (["07:30"], "2026-03-29T07:30:00+02:00", 24),
    ],
)
def test_window_tracks_previous_scheduled_interval_with_overlap(slots, now, expected):
    assert freshness_for_slots(slots, "Europe/Berlin", datetime.fromisoformat(now)) == expected


def test_delayed_run_does_not_expand_into_a_multi_day_catchup():
    now = datetime.fromisoformat("2026-11-25T20:00:00+01:00")
    assert freshness_for_slots(["15:30"], "Europe/Berlin", now) == 25
