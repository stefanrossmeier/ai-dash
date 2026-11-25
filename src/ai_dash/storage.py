from __future__ import annotations

import fcntl
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

from ai_dash.models import Artifact


@contextmanager
def exclusive(data_dir: Path):
    data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (data_dir / "pipeline.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("another ai-dash run holds the delivery lock") from None
        yield


class Store:
    def __init__(self, data_dir: Path):
        self.root = data_dir
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.db = sqlite3.connect(data_dir / "state.sqlite")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS editions (
                run_id TEXT PRIMARY KEY, artifact TEXT NOT NULL, destination TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS outbox (
                run_id TEXT NOT NULL, part INTEGER NOT NULL, body TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending', message_id INTEGER,
                PRIMARY KEY (run_id, part)
            );
        """)
        self.db.commit()

    def close(self):
        self.db.close()

    def history(self, now: datetime, days: int) -> list[dict]:
        result = []
        for (raw,) in self.db.execute("""
            SELECT artifact FROM editions e WHERE EXISTS (
                SELECT 1 FROM outbox o WHERE o.run_id=e.run_id AND o.status='sent'
            )
        """):
            artifact = Artifact.model_validate_json(raw)
            if artifact.created_at >= now - timedelta(days=days):
                # Retain delivered editions in history; unsent parts are never replayed.
                result.extend({"title": s.item.title, "url": s.item.url} for s in artifact.stories)
        return result

    def persist(self, artifact: Artifact, messages: list[str], destination: str):
        folder = self.root / "artifacts" / artifact.created_at.strftime("%Y/%m/%d")
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / (artifact.run_id + ".json")
        payload = artifact.model_dump_json(indent=2)
        # Exclusive create prevents accidental mutation of a run artifact.
        with path.open("x") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        descriptor = os.open(folder, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        with self.db:
            self.db.execute(
                "INSERT INTO editions VALUES (?, ?, ?)", (artifact.run_id, payload, destination)
            )
            self.db.executemany(
                "INSERT INTO outbox(run_id, part, body) VALUES (?, ?, ?)",
                [(artifact.run_id, n, text) for n, text in enumerate(messages)],
            )
        return path

    def pending(self) -> list[tuple]:
        return self.db.execute("""
            SELECT o.run_id, o.part, o.body, o.status, e.destination
            FROM outbox o JOIN editions e USING(run_id)
            WHERE o.status IN ('pending', 'sending') ORDER BY e.rowid, o.part
        """).fetchall()

    def discard_unsent(self) -> int:
        """Keep the audit trail, but never replay an older failed edition."""
        with self.db:
            return self.db.execute("""
                UPDATE outbox SET status=CASE WHEN status='sending'
                    THEN 'discarded_uncertain' ELSE 'discarded' END
                WHERE status IN ('pending', 'sending')
            """).rowcount

    def mark(self, run_id: str, part: int, state: str, message_id: int | None = None):
        with self.db:
            self.db.execute(
                "UPDATE outbox SET status=?, message_id=? WHERE run_id=? AND part=?",
                (state, message_id, run_id, part),
            )

    def resolve(self, run_id: str, part: int, state: str):
        with self.db:
            count = self.db.execute(
                """
                UPDATE outbox SET status=? WHERE run_id=? AND part=? AND status='sending'
            """,
                (state, run_id, part),
            ).rowcount
            if count != 1:
                raise ValueError("message is not awaiting uncertain-delivery resolution")

    def status(self) -> dict:
        reports = {}
        for (raw,) in self.db.execute("SELECT artifact FROM editions ORDER BY rowid DESC"):
            artifact = Artifact.model_validate_json(raw)
            if artifact.report_id not in reports:
                states = dict(
                    self.db.execute(
                        "SELECT status, COUNT(*) FROM outbox WHERE run_id=? GROUP BY status",
                        (artifact.run_id,),
                    )
                )
                parts = sum(states.values())
                acknowledged = states.get("sent", 0)
                if states.get("sending", 0) or states.get("discarded_uncertain", 0):
                    outcome = "uncertain"
                elif parts and acknowledged == parts:
                    outcome = "acknowledged"
                elif acknowledged:
                    outcome = "partial"
                elif states.get("pending", 0):
                    outcome = "pending"
                elif parts:
                    outcome = "discarded"
                else:
                    outcome = "missing" if artifact.stories else "not_required"
                reports[artifact.report_id] = {
                    "run_id": artifact.run_id,
                    "created_at": artifact.created_at.isoformat(),
                    "example": artifact.example,
                    "candidates": len(artifact.candidates),
                    "selected": len(artifact.stories),
                    "selection_outcome": "selected"
                    if artifact.stories
                    else "no_qualifying_stories",
                    "delivery": {
                        "outcome": outcome,
                        "parts": parts,
                        "acknowledged": acknowledged,
                        "states": states,
                    },
                    "health_warnings": artifact.health_warnings,
                }
        return {
            "reports": reports,
            "editions": self.db.execute("SELECT COUNT(*) FROM editions").fetchone()[0],
            "outbox": dict(self.db.execute("SELECT status, COUNT(*) FROM outbox GROUP BY status")),
            "unresolved": [
                {"run_id": r, "part": p, "status": s} for r, p, _, s, _ in self.pending()
            ],
        }
