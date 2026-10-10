from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path

from cognitive_sandbox.domain.models import ConversationEvent


class SQLiteEventStore:
    """Append-only conversation event storage; world and memory remain separate models."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """CREATE TABLE IF NOT EXISTS conversation_events (
                    id TEXT PRIMARY KEY,
                    world_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                )"""
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_world_time ON conversation_events(world_id, created_at)"
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def append(self, event: ConversationEvent) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """INSERT INTO conversation_events
                   (id, world_id, agent_id, kind, content, created_at, metadata_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (event.id, event.world_id, event.agent_id, event.kind, event.content,
                 event.created_at, json.dumps(event.metadata, ensure_ascii=False)),
            )

    def list_for_world(self, world_id: str) -> list[ConversationEvent]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT * FROM conversation_events WHERE world_id = ? ORDER BY rowid",
                (world_id,),
            ).fetchall()
        return [
            ConversationEvent(
                id=row["id"], world_id=row["world_id"], agent_id=row["agent_id"],
                kind=row["kind"], content=row["content"], created_at=row["created_at"],
                metadata=json.loads(row["metadata_json"]),
            )
            for row in rows
        ]
