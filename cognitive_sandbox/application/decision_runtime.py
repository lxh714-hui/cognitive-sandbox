from __future__ import annotations

from typing import Protocol

from cognitive_sandbox.application.action_generator import ActionGenerator
from cognitive_sandbox.application.action_scorer import ActionScorer
from cognitive_sandbox.application.action_selector import ActionSelector
from cognitive_sandbox.domain.actions import ActionProposal
from cognitive_sandbox.domain.cognition import (
    AgentCognitiveState,
    Goal,
    LongTermMemory,
    Relationship,
)


class CognitiveStateReader(Protocol):
    def get_state(self, agent_id: str) -> AgentCognitiveState: ...


class MotivationStateReader(Protocol):
    def list_goals_for_agent(self, agent_id: str) -> list[Goal]: ...
    def list_relationships_for_agent(self, agent_id: str) -> list[Relationship]: ...
    def list_long_term_memories(self, agent_id: str) -> list[LongTermMemory]: ...


class DecisionRuntime:
    """Orchestrate candidate generation, scoring, selection, and proposal creation."""
    def __init__(
        self,
        cognitive_state_reader: CognitiveStateReader,
        motivation_state_reader: MotivationStateReader | None = None,
        action_scorer: ActionScorer | None = None,
        action_generator: ActionGenerator | None = None,
        action_selector: ActionSelector | None = None,
    ) -> None:
        self._cognitive_state_reader = cognitive_state_reader
        self._motivation_state_reader = motivation_state_reader
        self._action_scorer = action_scorer or ActionScorer()
        self._action_generator = action_generator or ActionGenerator()
        self._action_selector = action_selector or ActionSelector()

    def generate_actions(self, agent_id: str) -> list[ActionProposal]:
        state = self._cognitive_state_reader.get_state(agent_id)
        if state.agent_id != agent_id:
            raise ValueError("Cognitive state reader returned a different agent's state.")
        goals = self._goals(agent_id)
        candidates = self._action_generator.generate(state, goals=goals)
        if not candidates:
            return []
        relationships = self._relationships(agent_id)
        memories = self._memories(agent_id)
        scores = self._action_scorer.score(
            state,
            candidates,
            goals=goals,
            relationships=relationships,
            memories=memories,
        )
        selection = self._action_selector.select(candidates, scores)
        if selection is None:
            return []
        candidate, score = selection
        metadata = dict(candidate.metadata)
        source_item_id = metadata.pop("source_working_memory_item_id")
        world_id = metadata.pop("world_id")
        branch_id = metadata.pop("branch_id")
        world_revision = metadata.pop("world_revision")
        return [
            ActionProposal(
                proposal_id=f"decision:{agent_id}:{source_item_id}:inspect-object",
                actor_id=agent_id,
                action_type=candidate.action_type,
                target_id=candidate.target_refs[0] if candidate.target_refs else None,
                payload={
                    **metadata,
                    "action_score": score.score,
                    "score_reasons": score.reasons,
                },
                branch_id=branch_id,
                world_id=world_id,
                base_world_revision=world_revision,
                priority=score.score,
            )
        ]

    def _goals(self, agent_id: str) -> list[Goal]:
        if self._motivation_state_reader is None:
            return []
        goals = self._motivation_state_reader.list_goals_for_agent(agent_id)
        if any(goal.agent_id != agent_id for goal in goals):
            raise ValueError("Goal reader returned a different agent's goal.")
        return goals

    def _relationships(self, agent_id: str) -> list[Relationship]:
        if self._motivation_state_reader is None:
            return []
        relationships = self._motivation_state_reader.list_relationships_for_agent(agent_id)
        if any(relationship.from_agent_id != agent_id for relationship in relationships):
            raise ValueError("Relationship reader returned a different agent's outgoing relationship.")
        return relationships

    def _memories(self, agent_id: str) -> list[LongTermMemory]:
        if self._motivation_state_reader is None:
            return []
        reader = getattr(self._motivation_state_reader, "list_long_term_memories", None)
        if reader is None:
            return []
        memories = reader(agent_id)
        if any(memory.agent_id != agent_id for memory in memories):
            raise ValueError("Memory reader returned another agent's long-term memory.")
        return memories
