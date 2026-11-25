import json
from datetime import timedelta

import pytest

from ai_dash.storage import Store
from tests.test_pipeline import artifact


@pytest.mark.parametrize(
    "selected,states,expected",
    [
        (False, [], "not_required"),
        (True, [], "missing"),
        (True, ["pending"], "pending"),
        (True, ["sent", "sent"], "acknowledged"),
        (False, ["sent"], "acknowledged"),  # An empty notice is not a selected story.
        (True, ["sent", "discarded"], "partial"),
        (True, ["discarded"], "discarded"),
        (True, ["sending"], "uncertain"),
        (True, ["sent", "discarded_uncertain"], "uncertain"),
    ],
)
def test_status_separates_selection_from_delivery(tmp_path, selected, states, expected):
    store = Store(tmp_path)
    report = artifact().model_copy(update={"stories": artifact().stories if selected else []})
    store.persist(report, ["PRIVATE_MESSAGE_BODY"] * len(states), "PRIVATE_DESTINATION")
    for part, state in enumerate(states):
        store.mark(report.run_id, part, state)
    status = store.status()
    row = status["reports"][report.report_id]
    assert row["selection_outcome"] == ("selected" if selected else "no_qualifying_stories")
    assert row["selected"] == int(selected)
    assert row["delivery"]["outcome"] == expected
    assert row["delivery"]["acknowledged"] == states.count("sent")
    assert row["delivery"]["parts"] == len(states)
    assert "PRIVATE_MESSAGE_BODY" not in json.dumps(status)
    assert "PRIVATE_DESTINATION" not in json.dumps(status)
    store.close()


def test_status_uses_latest_persisted_edition_per_report(tmp_path):
    store = Store(tmp_path)
    first = artifact()
    store.persist(first, ["old acknowledged message"], "private")
    store.mark(first.run_id, 0, "sent")
    quiet = first.model_copy(
        update={
            "run_id": "new-quiet",
            "created_at": first.created_at + timedelta(hours=1),
            "stories": [],
            "example": True,
        }
    )
    store.persist(quiet, [], "private")
    row = store.status()["reports"][first.report_id]
    assert row["run_id"] == "new-quiet" and row["example"] is True
    assert row["selected"] == 0 and row["delivery"]["outcome"] == "not_required"
    assert store.status()["outbox"] == {"sent": 1}
    store.close()
