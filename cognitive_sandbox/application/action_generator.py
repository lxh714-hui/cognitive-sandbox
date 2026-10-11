from __future__ import annotations

import re

from cognitive_sandbox.domain.actions import ActionCandidate
from cognitive_sandbox.domain.cognition import AgentCognitiveState, Goal


class ActionGenerator:
    """Create deterministic action candidates from one agent's current cognition."""

    _BROKEN_OBJECT = re.compile(
        r"\bbroke object\s+([^\s.]+)|物体\s+([^\s，。]+)\s+碎裂",
        re.IGNORECASE,
    )

    def generate(
        self,
        state: AgentCognitiveState,
        *,
        goals: tuple[Goal, ...] | list[Goal] = (),
    ) -> list[ActionCandidate]:
        if not isinstance(state, AgentCognitiveState):
            raise TypeError("state must be an AgentCognitiveState.")
        goals = tuple(goals)
        if any(goal.agent_id != state.agent_id for goal in goals):
            raise ValueError("Goals must belong to the candidate agent.")
        if not state.working_memory:
            return []

        item = state.working_memory[-1]
        text = item.content.get("text")
        if item.agent_id != state.agent_id or not isinstance(text, str):
            return []
        match = self._BROKEN_OBJECT.search(text)
        if match is None:
            return []
        active_investigate_goals = [
            goal for goal in goals if goal.goal_type == "investigate" and goal.status == "active"
        ]
        if not active_investigate_goals and (
            state.emotion_state.valence >= 0 or state.emotion_state.arousal <= 0
        ):
            return []

        metadata = {
            "source_working_memory_item_id": item.item_id,
            "world_id": item.content.get("world_id"),
            "branch_id": item.content.get("branch_id"),
            "world_revision": item.content.get("world_revision"),
            "observation_id": item.content.get("observation_id"),
            "source_event_ids": item.content.get("source_event_ids"),
            "decision_rule": (
                "investigate_goal_after_observing_damage"
                if active_investigate_goals
                else "inspect_object_after_observing_damage"
            ),
        }
        if (
            not isinstance(metadata["world_id"], str)
            or not metadata["world_id"].strip()
            or not isinstance(metadata["branch_id"], str)
            or not metadata["branch_id"].strip()
            or isinstance(metadata["world_revision"], bool)
            or not isinstance(metadata["world_revision"], int)
            or metadata["world_revision"] < 0
            or not isinstance(metadata["observation_id"], str)
            or not metadata["observation_id"].strip()
            or not isinstance(metadata["source_event_ids"], tuple)
            or not metadata["source_event_ids"]
        ):
            return []

        object_id = match.group(1) or match.group(2)
        return [
            ActionCandidate(
                action_type="INSPECT_OBJECT",
                target_refs=(object_id,),
                metadata=metadata,
            )
        ]
