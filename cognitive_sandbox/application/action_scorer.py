from __future__ import annotations

import re
from collections.abc import Iterable, Sequence

from cognitive_sandbox.domain.actions import ActionCandidate, ActionScore
from cognitive_sandbox.domain.cognition import (
    AgentCognitiveState,
    Goal,
    LongTermMemory,
    Relationship,
)


class ActionScorer:
    """Score already-proposed candidates from one agent's private state."""

    _DAMAGE_TERMS = re.compile(r"\b(?:break|broke|broken|damage|damaged)\b|碎|破|损", re.IGNORECASE)
    _GOAL_ACTIONS = {
        "investigate": {"INSPECT_OBJECT"},
        "protect": {"PROTECT", "DEFEND", "PROTECT_OBJECT"},
        "maintain": {"MAINTAIN", "REPAIR", "RESTORE"},
    }

    def score(
        self,
        state: AgentCognitiveState,
        candidates: Sequence[ActionCandidate],
        *,
        goals: Iterable[Goal] = (),
        relationships: Iterable[Relationship] = (),
        memories: Iterable[LongTermMemory] = (),
    ) -> list[ActionScore]:
        if not isinstance(state, AgentCognitiveState):
            raise TypeError("state must be an AgentCognitiveState.")
        goals = tuple(goals)
        relationships = tuple(relationships)
        memories = tuple(memories)
        if any(goal.agent_id != state.agent_id for goal in goals):
            raise ValueError("Goals must belong to the scored agent.")
        if any(relationship.from_agent_id != state.agent_id for relationship in relationships):
            raise ValueError("Relationships must be outgoing from the scored agent.")
        if any(memory.agent_id != state.agent_id for memory in memories):
            raise ValueError("Memories must belong to the scored agent.")

        scores: list[ActionScore] = []
        for candidate in candidates:
            if not isinstance(candidate, ActionCandidate):
                raise TypeError("candidates must contain ActionCandidate values.")
            target_id = candidate.target_refs[0] if candidate.target_refs else None

            evidence_strength = max(
                (
                    item.priority
                    for item in state.working_memory
                    if item.agent_id == state.agent_id
                    and self._supports_action(
                        str(item.content.get("text", "")), candidate.action_type, target_id
                    )
                ),
                default=0.0,
            )
            belief_strength = max(
                (
                    belief.confidence
                    for belief in state.beliefs
                    if self._supports_action(
                        belief.proposition, candidate.action_type, target_id
                    )
                ),
                default=0.0,
            )
            memory_strength = max(
                (
                    memory.salience
                    for memory in memories
                    if self._supports_action(
                        " ".join(str(value) for value in memory.content.values()),
                        candidate.action_type,
                        target_id,
                    )
                ),
                default=0.0,
            )
            emotion_strength = min(
                1.0,
                max(0.0, -state.emotion_state.valence) * state.emotion_state.arousal,
            )
            matching_goals = [
                goal
                for goal in goals
                if goal.status == "active"
                and candidate.action_type in self._GOAL_ACTIONS.get(goal.goal_type, set())
            ]
            goal_strength = max((goal.priority for goal in matching_goals), default=0.0)
            high_trust = max(
                (relationship.trust for relationship in relationships if relationship.trust >= 0.7),
                default=0.0,
            )

            # Fixed, transparent weights keep the score deterministic and bounded.
            score = (
                0.10
                + 0.20 * evidence_strength
                + 0.20 * belief_strength
                + 0.15 * memory_strength
                + 0.15 * emotion_strength
                + 0.12 * goal_strength
                + 0.08 * high_trust
            )
            reasons = ["baseline_candidate"]
            if evidence_strength:
                reasons.append("supported_by_working_memory")
            if belief_strength:
                reasons.append("supported_by_belief")
            if memory_strength:
                reasons.append("supported_by_long_term_memory")
            if emotion_strength:
                reasons.append("emotion_signal")
            if matching_goals:
                reasons.append("active_goal_match")
            if high_trust:
                reasons.append("high_trust_relationship")
            scores.append(
                ActionScore(
                    action_type=candidate.action_type,
                    score=min(1.0, score),
                    reasons=tuple(reasons),
                )
            )
        return scores

    @classmethod
    def _supports_action(cls, text: str, action_type: str, target_id: str | None) -> bool:
        if target_id and target_id.casefold() in text.casefold():
            return True
        return action_type == "INSPECT_OBJECT" and bool(cls._DAMAGE_TERMS.search(text))
