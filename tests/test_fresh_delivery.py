from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from ai_dash.models import Coverage, Settings, Story
from ai_dash.pipeline import run
from ai_dash.storage import Store
from tests.test_pipeline import artifact, item


def fresh_collector(monkeypatch):
    calls = []

    def collect(*args, **kwargs):
        calls.append(len(calls) + 1)
        fresh = item(
            f"Fresh retrieval {len(calls)}",
            f"https://example.org/fresh-{len(calls)}",
            datetime.now(UTC) - timedelta(minutes=5),
        )
        return [fresh], [Coverage(source_id="test", status="ok", items=1, fresh=1)]

    monkeypatch.setattr("ai_dash.pipeline.collect", collect)
    monkeypatch.setattr(
        "ai_dash.pipeline.rank",
        lambda items, *a, **kw: [Story(item=i, score=80, summary="A fresh report.") for i in items],
    )
    monkeypatch.setattr("ai_dash.delivery.time.sleep", lambda _: None)
    return calls


@pytest.mark.parametrize("status", ["pending", "sending"])
def test_next_run_discards_old_unsent_editions_and_retrieves_fresh(monkeypatch, tmp_path, status):
    store = Store(tmp_path)
    store.persist(artifact(), ["OLD BUFFERED MESSAGE"], "@ai")
    store.mark("test-run", 0, status)
    store.close()
    calls = fresh_collector(monkeypatch)
    sent = []

    class Telegram:
        def check(self, destination):
            pass

        def call(self, method, body):
            sent.append(body["text"])
            return {"message_id": 1}

    result = run(
        Settings(sources=[]),
        SimpleNamespace(traces=[]),
        tmp_path / "unused",
        tmp_path,
        Telegram(),
        "@ai",
    )
    assert calls == [1] and result["messages_discarded"] == 1
    assert result["messages_resumed"] == 0
    assert len(sent) == 1 and "Fresh retrieval 1" in sent[0]
    assert "OLD BUFFERED MESSAGE" not in sent[0]
    store = Store(tmp_path)
    expected = "discarded_uncertain" if status == "sending" else "discarded"
    assert (
        store.db.execute("select status from outbox where run_id='test-run'").fetchone()[0]
        == expected
    )
    assert store.pending() == []
    store.close()


def test_delivery_outage_discards_report_and_recovery_collects_again(monkeypatch, tmp_path):
    calls = fresh_collector(monkeypatch)
    sent = []

    class Telegram:
        failing = True

        def check(self, destination):
            pass

        def call(self, method, body):
            if self.failing:
                raise RuntimeError("Telegram transport failed")
            sent.append(body["text"])
            return {"message_id": 2}

    telegram = Telegram()
    args = (
        Settings(sources=[]),
        SimpleNamespace(traces=[]),
        tmp_path / "unused",
        tmp_path,
        telegram,
        "@ai",
    )
    with pytest.raises(RuntimeError, match="transport"):
        run(*args)
    store = Store(tmp_path)
    assert store.pending() == []
    assert store.status()["outbox"] == {"discarded_uncertain": 1}
    store.close()
    telegram.failing = False
    run(*args)
    assert calls == [1, 2]
    assert len(sent) == 1 and "Fresh retrieval 2" in sent[0]
    assert "Fresh retrieval 1" not in sent[0]
