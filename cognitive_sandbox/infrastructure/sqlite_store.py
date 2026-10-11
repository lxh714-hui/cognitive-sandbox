from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from cognitive_sandbox.domain.cognition import (
    AgentCognitiveState,
    Belief,
    CognitiveUpdateProposal,
    EmotionState,
    Goal,
    LongTermMemory,
    ProposalOperation,
    Relationship,
    WorkingMemoryItem,
)
from cognitive_sandbox.domain.models import ConversationEvent
from cognitive_sandbox.domain.story import (
    BranchSimulationRecord,
    ConstraintEvaluation,
    StorySimulationResult,
)
from cognitive_sandbox.domain.world_events import WorldEvent


def _json_payload(value: Any) -> Any:
    """Convert the immutable WorldEvent payload back to JSON containers."""
    if isinstance(value, Mapping):
        return {key: _json_payload(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_payload(item) for item in value]
    if isinstance(value, frozenset):
        return [_json_payload(item) for item in value]
    return value


def _state_payload(state: AgentCognitiveState) -> dict[str, Any]:
    return {
        "agent_id": state.agent_id,
        "cognitive_revision": state.cognitive_revision,
        "working_memory": [
            {
                "item_id": item.item_id,
                "agent_id": item.agent_id,
                "content": _json_payload(item.content),
                "source_refs": list(item.source_refs),
                "priority": item.priority,
                "created_at": item.created_at,
            }
            for item in state.working_memory
        ],
        "emotion_state": {
            "valence": state.emotion_state.valence,
            "arousal": state.emotion_state.arousal,
            "source_refs": list(state.emotion_state.source_refs),
            "updated_at": state.emotion_state.updated_at,
        },
        "beliefs": [
            {
                "belief_id": belief.belief_id,
                "agent_id": belief.agent_id,
                "belief_type": belief.belief_type,
                "proposition": belief.proposition,
                "confidence": belief.confidence,
                "source_refs": list(belief.source_refs),
            }
            for belief in state.beliefs
        ],
    }


def _state_from_payload(payload: Mapping[str, Any]) -> AgentCognitiveState:
    emotion = payload["emotion_state"]
    return AgentCognitiveState(
        agent_id=payload["agent_id"],
        cognitive_revision=payload["cognitive_revision"],
        working_memory=tuple(
            WorkingMemoryItem(
                item_id=item["item_id"],
                agent_id=item["agent_id"],
                content=item["content"],
                source_refs=tuple(item["source_refs"]),
                priority=item["priority"],
                created_at=item["created_at"],
            )
            for item in payload["working_memory"]
        ),
        emotion_state=EmotionState(
            valence=emotion["valence"],
            arousal=emotion["arousal"],
            source_refs=tuple(emotion["source_refs"]),
            updated_at=emotion["updated_at"],
        ),
        beliefs=tuple(
            Belief(
                belief_id=belief["belief_id"],
                agent_id=belief["agent_id"],
                belief_type=belief["belief_type"],
                proposition=belief["proposition"],
                confidence=belief["confidence"],
                source_refs=tuple(belief["source_refs"]),
            )
            for belief in payload.get("beliefs", ())
        ),
    )


def _story_result_payload(result: StorySimulationResult) -> dict[str, Any]:
    return {
        "simulation_id": result.simulation_id,
        "success": result.success,
        "steps": result.steps,
        "events": [
            {
                "event_id": event.event_id,
                "branch_id": event.branch_id,
                "world_id": event.world_id,
                "event_type": event.event_type,
                "actor_id": event.actor_id,
                "payload": _json_payload(event.payload),
                "world_revision": event.world_revision,
            }
            for event in result.events
        ],
        "evaluation": {
            "world_event_id": result.evaluation.world_event_id,
            "accepted": result.evaluation.accepted,
            "hard_violations": list(result.evaluation.hard_violations),
            "soft_score": result.evaluation.soft_score,
            "matched_soft_constraints": list(result.evaluation.matched_soft_constraints),
            "source_event_ids": list(result.evaluation.source_event_ids),
        },
    }


def _story_result_from_payload(payload: Mapping[str, Any]) -> StorySimulationResult:
    evaluation = payload["evaluation"]
    return StorySimulationResult(
        simulation_id=payload["simulation_id"],
        success=payload["success"],
        steps=payload["steps"],
        events=tuple(
            WorldEvent(
                event_id=event["event_id"],
                branch_id=event["branch_id"],
                world_id=event["world_id"],
                event_type=event["event_type"],
                actor_id=event["actor_id"],
                payload=event["payload"],
                world_revision=event["world_revision"],
            )
            for event in payload["events"]
        ),
        evaluation=ConstraintEvaluation(
            world_event_id=evaluation["world_event_id"],
            accepted=evaluation["accepted"],
            hard_violations=tuple(evaluation["hard_violations"]),
            soft_score=evaluation["soft_score"],
            matched_soft_constraints=tuple(evaluation["matched_soft_constraints"]),
            source_event_ids=tuple(evaluation["source_event_ids"]),
        ),
    )


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
                """CREATE TABLE IF NOT EXISTS world_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    branch_id TEXT NOT NULL,
                    world_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    world_revision INTEGER NOT NULL CHECK (world_revision >= 0),
                    created_at TEXT NOT NULL
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS agent_cognitive_states (
                    agent_id TEXT PRIMARY KEY,
                    cognitive_revision INTEGER NOT NULL CHECK (cognitive_revision >= 1),
                    state_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS cognitive_change_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    proposal_id TEXT UNIQUE NOT NULL,
                    agent_id TEXT NOT NULL,
                    cognitive_revision INTEGER NOT NULL CHECK (cognitive_revision >= 1),
                    target_layer TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    source_refs_json TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    world_revision INTEGER NOT NULL CHECK (world_revision >= 0),
                    state_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(agent_id, cognitive_revision)
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS long_term_memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_id TEXT UNIQUE NOT NULL,
                    agent_id TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    content_json TEXT NOT NULL,
                    source_refs_json TEXT NOT NULL,
                    salience REAL NOT NULL CHECK (salience >= 0 AND salience <= 1),
                    created_at TEXT NOT NULL,
                    UNIQUE(agent_id, source_refs_json)
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS goals (
                    goal_id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    goal_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    priority REAL NOT NULL CHECK (priority >= 0 AND priority <= 1),
                    status TEXT NOT NULL,
                    source_refs_json TEXT NOT NULL
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS relationships (
                    relationship_id TEXT PRIMARY KEY,
                    from_agent_id TEXT NOT NULL,
                    to_agent_id TEXT NOT NULL,
                    trust REAL NOT NULL CHECK (trust >= 0 AND trust <= 1),
                    affinity REAL NOT NULL CHECK (affinity >= 0 AND affinity <= 1),
                    hostility REAL NOT NULL CHECK (hostility >= 0 AND hostility <= 1),
                    source_refs_json TEXT NOT NULL
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS agent_beliefs (
                    belief_id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    belief_type TEXT NOT NULL,
                    proposition TEXT NOT NULL,
                    confidence REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
                    source_refs_json TEXT NOT NULL
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS branch_simulations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    simulation_id TEXT UNIQUE NOT NULL,
                    branch_id TEXT NOT NULL,
                    result_status TEXT NOT NULL CHECK (
                        result_status IN ('pending', 'succeeded', 'failed')
                    ),
                    result_json TEXT
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

    def append_world_event(self, event: WorldEvent) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """INSERT INTO world_events
                   (event_id, branch_id, world_id, event_type, actor_id,
                    payload_json, world_revision, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    event.event_id,
                    event.branch_id,
                    event.world_id,
                    event.event_type,
                    event.actor_id,
                    json.dumps(_json_payload(event.payload), ensure_ascii=False),
                    event.world_revision,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def list_world_events(self, world_id: str) -> list[WorldEvent]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT * FROM world_events WHERE world_id = ? ORDER BY id",
                (world_id,),
            ).fetchall()
        return [
            WorldEvent(
                event_id=row["event_id"],
                branch_id=row["branch_id"],
                world_id=row["world_id"],
                event_type=row["event_type"],
                actor_id=row["actor_id"],
                payload=json.loads(row["payload_json"]),
                world_revision=row["world_revision"],
            )
            for row in rows
        ]

    def get_world_event(self, event_id: str) -> WorldEvent | None:
        """Read one committed source event without loading the world's event history."""
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT * FROM world_events WHERE event_id = ?",
                (event_id,),
            ).fetchone()
        if row is None:
            return None
        return WorldEvent(
            event_id=row["event_id"],
            branch_id=row["branch_id"],
            world_id=row["world_id"],
            event_type=row["event_type"],
            actor_id=row["actor_id"],
            payload=json.loads(row["payload_json"]),
            world_revision=row["world_revision"],
        )

    def get_cognitive_state(self, agent_id: str) -> AgentCognitiveState | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT state_json FROM agent_cognitive_states WHERE agent_id = ?",
                (agent_id,),
            ).fetchone()
        if row is None:
            return None
        return _state_from_payload(json.loads(row["state_json"]))

    def commit_cognitive_update(
        self,
        proposal: CognitiveUpdateProposal,
        state: AgentCognitiveState,
    ) -> bool:
        """Atomically append the cognitive change and replace the agent's current state."""
        if proposal.agent_id != state.agent_id:
            raise ValueError("Proposal and state agent IDs must match.")
        if state.cognitive_revision != proposal.base_cognitive_revision + 1:
            raise ValueError("Committed cognitive revision must increment exactly once.")
        serialized_state = json.dumps(_state_payload(state), ensure_ascii=False)
        created_at = datetime.now(timezone.utc).isoformat()
        with closing(self._connect()) as connection, connection:
            row = connection.execute(
                "SELECT cognitive_revision, state_json FROM agent_cognitive_states WHERE agent_id = ?",
                (proposal.agent_id,),
            ).fetchone()
            actual_revision = row["cognitive_revision"] if row is not None else 0
            if actual_revision != proposal.base_cognitive_revision:
                return False
            previous_state = (
                _state_from_payload(json.loads(row["state_json"]))
                if row is not None
                else AgentCognitiveState(agent_id=proposal.agent_id)
            )
            previous_beliefs = {belief.belief_id: belief for belief in previous_state.beliefs}
            next_beliefs = {belief.belief_id: belief for belief in state.beliefs}
            if any(next_beliefs.get(belief_id) != belief for belief_id, belief in previous_beliefs.items()):
                raise ValueError("Cognitive updates cannot remove or rewrite existing beliefs.")
            new_beliefs = [
                belief for belief in state.beliefs if belief.belief_id not in previous_beliefs
            ]
            for belief in new_beliefs:
                if belief.agent_id != proposal.agent_id:
                    raise ValueError("A cognitive update cannot commit another agent's belief.")
                if not set(belief.source_refs).issubset(proposal.source_refs):
                    raise ValueError("A new belief must cite the cognitive proposal's sources.")
                connection.execute(
                    """INSERT INTO agent_beliefs
                       (belief_id, agent_id, belief_type, proposition, confidence, source_refs_json)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        belief.belief_id,
                        belief.agent_id,
                        belief.belief_type,
                        belief.proposition,
                        belief.confidence,
                        json.dumps(list(belief.source_refs), ensure_ascii=False),
                    ),
                )
            connection.execute(
                """INSERT INTO cognitive_change_history
                   (proposal_id, agent_id, cognitive_revision, target_layer, operation,
                    source_refs_json, reason, world_revision, state_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    proposal.proposal_id,
                    proposal.agent_id,
                    state.cognitive_revision,
                    proposal.target_layer,
                    proposal.operation.value,
                    json.dumps(list(proposal.source_refs), ensure_ascii=False),
                    proposal.reason,
                    proposal.world_revision,
                    serialized_state,
                    created_at,
                ),
            )
            connection.execute(
                """INSERT INTO agent_cognitive_states
                   (agent_id, cognitive_revision, state_json, updated_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(agent_id) DO UPDATE SET
                       cognitive_revision = excluded.cognitive_revision,
                       state_json = excluded.state_json,
                       updated_at = excluded.updated_at""",
                (proposal.agent_id, state.cognitive_revision, serialized_state, created_at),
            )
        return True

    def list_cognitive_change_history(self, agent_id: str) -> list[dict[str, Any]]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT * FROM cognitive_change_history WHERE agent_id = ? ORDER BY id",
                (agent_id,),
            ).fetchall()
        return [
            {
                "proposal_id": row["proposal_id"],
                "agent_id": row["agent_id"],
                "cognitive_revision": row["cognitive_revision"],
                "target_layer": row["target_layer"],
                "operation": ProposalOperation(row["operation"]),
                "source_refs": tuple(json.loads(row["source_refs_json"])),
                "reason": row["reason"],
                "world_revision": row["world_revision"],
                "state": _state_from_payload(json.loads(row["state_json"])),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def list_beliefs_for_agent(self, agent_id: str) -> list[Belief]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT * FROM agent_beliefs WHERE agent_id = ? ORDER BY rowid",
                (agent_id,),
            ).fetchall()
        return [
            Belief(
                belief_id=row["belief_id"],
                agent_id=row["agent_id"],
                belief_type=row["belief_type"],
                proposition=row["proposition"],
                confidence=row["confidence"],
                source_refs=tuple(json.loads(row["source_refs_json"])),
            )
            for row in rows
        ]

    def append_long_term_memory(self, memory: LongTermMemory) -> bool:
        """Persist one encoded observation memory; return False for a duplicate source."""
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                """INSERT INTO long_term_memories
                   (memory_id, agent_id, memory_type, content_json, source_refs_json,
                    salience, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(agent_id, source_refs_json) DO NOTHING""",
                (
                    memory.memory_id,
                    memory.agent_id,
                    memory.memory_type,
                    json.dumps(_json_payload(memory.content), ensure_ascii=False),
                    json.dumps(list(memory.source_refs), ensure_ascii=False),
                    memory.salience,
                    memory.created_at,
                ),
            )
        return cursor.rowcount == 1

    def list_long_term_memories(self, agent_id: str) -> list[LongTermMemory]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT * FROM long_term_memories WHERE agent_id = ? ORDER BY id",
                (agent_id,),
            ).fetchall()
        return [
            LongTermMemory(
                memory_id=row["memory_id"],
                agent_id=row["agent_id"],
                memory_type=row["memory_type"],
                content=json.loads(row["content_json"]),
                source_refs=tuple(json.loads(row["source_refs_json"])),
                salience=row["salience"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def append_goal(self, goal: Goal) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """INSERT INTO goals
                   (goal_id, agent_id, goal_type, description, priority, status, source_refs_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    goal.goal_id,
                    goal.agent_id,
                    goal.goal_type,
                    goal.description,
                    goal.priority,
                    goal.status,
                    json.dumps(list(goal.source_refs), ensure_ascii=False),
                ),
            )

    def list_goals_for_agent(self, agent_id: str) -> list[Goal]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT * FROM goals WHERE agent_id = ? ORDER BY rowid",
                (agent_id,),
            ).fetchall()
        return [
            Goal(
                goal_id=row["goal_id"],
                agent_id=row["agent_id"],
                goal_type=row["goal_type"],
                description=row["description"],
                priority=row["priority"],
                status=row["status"],
                source_refs=tuple(json.loads(row["source_refs_json"])),
            )
            for row in rows
        ]

    def append_relationship(self, relationship: Relationship) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """INSERT INTO relationships
                   (relationship_id, from_agent_id, to_agent_id, trust, affinity,
                    hostility, source_refs_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    relationship.relationship_id,
                    relationship.from_agent_id,
                    relationship.to_agent_id,
                    relationship.trust,
                    relationship.affinity,
                    relationship.hostility,
                    json.dumps(list(relationship.source_refs), ensure_ascii=False),
                ),
            )

    def list_relationships_for_agent(self, agent_id: str) -> list[Relationship]:
        """Return this agent's outgoing relationships; direction is never reversed."""
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT * FROM relationships WHERE from_agent_id = ? ORDER BY rowid",
                (agent_id,),
            ).fetchall()
        return [
            Relationship(
                relationship_id=row["relationship_id"],
                from_agent_id=row["from_agent_id"],
                to_agent_id=row["to_agent_id"],
                trust=row["trust"],
                affinity=row["affinity"],
                hostility=row["hostility"],
                source_refs=tuple(json.loads(row["source_refs_json"])),
            )
            for row in rows
        ]

    def create_branch_simulation(self, record: BranchSimulationRecord) -> None:
        if not isinstance(record, BranchSimulationRecord):
            raise TypeError("record must be a BranchSimulationRecord.")
        if record.result_status != "pending":
            raise ValueError("A new branch simulation must start with pending status.")
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """INSERT INTO branch_simulations
                   (simulation_id, branch_id, result_status, result_json)
                   VALUES (?, ?, ?, NULL)""",
                (record.simulation_id, record.branch_id, record.result_status),
            )

    def complete_branch_simulation(self, result: StorySimulationResult) -> BranchSimulationRecord:
        if not isinstance(result, StorySimulationResult):
            raise TypeError("result must be a StorySimulationResult.")
        serialized = json.dumps(_story_result_payload(result), ensure_ascii=False)
        status = "succeeded" if result.success else "failed"
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                """UPDATE branch_simulations
                   SET result_status = ?, result_json = ?
                   WHERE simulation_id = ? AND result_status = 'pending'""",
                (status, serialized, result.simulation_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("No pending branch simulation exists for this result.")
            row = connection.execute(
                "SELECT simulation_id, branch_id, result_status FROM branch_simulations "
                "WHERE simulation_id = ?",
                (result.simulation_id,),
            ).fetchone()
        return BranchSimulationRecord(
            simulation_id=row["simulation_id"],
            branch_id=row["branch_id"],
            result_status=row["result_status"],
        )

    def get_branch_simulation(self, simulation_id: str) -> BranchSimulationRecord | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT simulation_id, branch_id, result_status FROM branch_simulations "
                "WHERE simulation_id = ?",
                (simulation_id,),
            ).fetchone()
        if row is None:
            return None
        return BranchSimulationRecord(
            simulation_id=row["simulation_id"],
            branch_id=row["branch_id"],
            result_status=row["result_status"],
        )

    def list_branch_simulations(self, branch_id: str) -> list[BranchSimulationRecord]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT simulation_id, branch_id, result_status FROM branch_simulations "
                "WHERE branch_id = ? ORDER BY id",
                (branch_id,),
            ).fetchall()
        return [
            BranchSimulationRecord(
                simulation_id=row["simulation_id"],
                branch_id=row["branch_id"],
                result_status=row["result_status"],
            )
            for row in rows
        ]

    def get_branch_simulation_result(self, simulation_id: str) -> StorySimulationResult | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT result_json FROM branch_simulations WHERE simulation_id = ?",
                (simulation_id,),
            ).fetchone()
        if row is None or row["result_json"] is None:
            return None
        return _story_result_from_payload(json.loads(row["result_json"]))
