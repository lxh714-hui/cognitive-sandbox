from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from cognitive_sandbox.knowledge.retrieval.knowledge_query import KnowledgeQuery


@dataclass(frozen=True)
class DebugReport:
    generated_at: str
    text: str
    character_id: str | None = None

    def __post_init__(self):
        if not isinstance(self.generated_at, str) or not self.generated_at.strip():
            raise ValueError("generated_at must not be empty.")
        if not isinstance(self.text, str) or not self.text.strip():
            raise ValueError("text must not be empty.")
        if self.character_id is not None and (
            not isinstance(self.character_id, str) or not self.character_id.strip()
        ):
            raise ValueError("character_id must be None or non-empty.")


class DebugReportBuilder:
    """Build a read-only, human-readable explanation from registered snapshots."""

    def build(self, session, *, character_id: str | None = None, knowledge_query: str = "") -> DebugReport:
        executor = session.executor
        scenario = getattr(session, "scenario_content", None)
        document = getattr(scenario, "world_document", None)
        name = getattr(document, "name", None) or getattr(getattr(session, "scenario", None), "name", None) or session.world_instance_id
        clock = getattr(executor, "world_clock", None)
        now = clock.current_time().isoformat() if clock is not None else "unavailable"
        lines = [f"# {name or 'World'} simulation report", f"Generated: {datetime.now(timezone.utc).isoformat()}",
                 f"World ID: {executor.world_id}", f"Time: {now}"]

        timeline = getattr(executor, "event_timeline", None)
        records = tuple(getattr(timeline, "events", ()))
        lines.extend(("", f"## Event history ({len(records)})"))
        for record in records[-30:]:
            description = record.metadata.get("description") or record.event_type
            lines.append(f"- {record.timestamp} · {record.event_type} · {description} [{record.event_id}]")

        engine = getattr(executor, "world_evolution_engine", None)
        changes = tuple(getattr(engine, "state_changes", ()))
        lines.extend(("", f"## State changes ({len(changes)})"))
        for change in changes[-60:]:
            lines.append(
                f"- {change.target_type}:{change.target_id}.{change.field}: "
                f"{change.old_value!s} → {change.new_value!s} — {change.reason}"
            )

        goals = tuple(getattr(getattr(executor, "goal_manager", None), "goals", ()))
        lines.extend(("", f"## Goals ({len(goals)})"))
        for goal in goals:
            lines.append(
                f"- {goal.owner_id}: {goal.description} · {goal.progress:.0%} · {goal.status}"
            )

        if character_id is not None:
            retriever = getattr(session, "knowledge_retriever", None) or getattr(executor, "knowledge_retriever", None)
            if retriever is None:
                raise ValueError("character knowledge retrieval is unavailable.")
            records = retriever.retrieve(character_id, KnowledgeQuery(text=knowledge_query, limit=50))
            visible = tuple(
                record for record in records
                if record.visibility.allows(character_id, record.owner_id)
            )
            lines.extend(("", f"## Knowledge visible to {character_id} ({len(visible)})"))
            for record in visible:
                content = record.known_content
                if not content:
                    store = getattr(retriever, "backing_store", None)
                    fact = store.get_fact(record.fact_id) if store is not None else None
                    content = getattr(fact, "content", "")
                if content:
                    lines.append(
                        f"- {content} · {record.knowledge_type.value} · "
                        f"confidence {record.confidence:.2f} · {record.source.source_type}"
                    )
        return DebugReport(datetime.now(timezone.utc).isoformat(), "\n".join(lines), character_id)
