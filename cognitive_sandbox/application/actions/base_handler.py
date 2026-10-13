from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping
from typing import Any, Protocol

from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.roleplay_turn import RoleplayTurn


@dataclass
class ActionExecutionContext:
    turn: RoleplayTurn
    agent_context: AgentContext
    agent_contexts: tuple[AgentContext, ...]
    world_state: Mapping[str, Any]
    situation: str
    target: AgentContext | None = None
    scenario_content: Any = None
    world_id: str = "world"
    branch_id: str = "main"
    knowledge_store: Any = None
    knowledge_retriever: Any = None
    narrative_formatter: Any = None
    dialogue_service: Any = None
    character_minds: Mapping[str, Any] | None = None
    simulation_tick: Any = None
    event_timeline: Any = None
    relationship_manager: Any = None
    event_pipeline: Any = None
    world_clock: Any = None
    time_scheduler: Any = None
    resource_manager: Any = None
    location_manager: Any = None
    presence_manager: Any = None
    motivation_manager: Any = None
    goal_manager: Any = None
    narrative_pressure: Any = None
    emotion_engine: Any = None
    authority_manager: Any = None
    cognitive_engine: Any = None
    narrative_context: Any = None


class ActionHandler(Protocol):
    def handle(self, action, context: ActionExecutionContext): ...
