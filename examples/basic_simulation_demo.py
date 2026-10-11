"""Run one small end-to-end Cognitive Sandbox simulation tick."""

from __future__ import annotations

from typing import Any

from cognitive_sandbox.application.action_decision import ActionDecisionEngine
from cognitive_sandbox.application.action_event_adapter import ActionEventAdapter
from cognitive_sandbox.application.action_resolver import ActionResolver
from cognitive_sandbox.application.agent_context_builder import AgentContextBuilder
from cognitive_sandbox.application.agent_state_updater import AgentStateUpdater
from cognitive_sandbox.application.character_initializer import (
    CharacterInitializationRequest,
    CharacterInitializer,
)
from cognitive_sandbox.application.memory_initializer import MemoryInitializer
from cognitive_sandbox.application.memory_updater import MemoryUpdater
from cognitive_sandbox.application.relationship_initializer import RelationshipInitializer
from cognitive_sandbox.application.relationship_updater import RelationshipUpdater
from cognitive_sandbox.application.simulation_tick import SimulationTick
from cognitive_sandbox.application.world_state_applier import WorldStateApplier
from cognitive_sandbox.application.world_state_updater import WorldStateUpdater
from cognitive_sandbox.domain.agent_state import AgentDynamicState


def run_demo() -> dict[str, Any]:
    world_state = {
        "social_trust": 0.5,
        "danger_level": 0.5,
    }
    character = CharacterInitializer(character_id_factory=lambda: "doctor-1").initialize(
        CharacterInitializationRequest("医生")
    )
    memories = MemoryInitializer(memory_id_factory=lambda: "memory-initial").initialize("医生")
    relationships = RelationshipInitializer().initialize("医生", source_id=character.character_id)
    dynamic_state = AgentDynamicState(
        character_id=character.character_id,
        confidence=0.5,
        stress=0.1,
        motivation=0.6,
    )
    context_builder = AgentContextBuilder()
    agent_context = context_builder.build(
        character,
        memories,
        relationships,
        world_state,
        dynamic_state=dynamic_state,
    )

    tick = SimulationTick(
        ActionDecisionEngine(action_id_factory=iter(("action-help", "action-observe")).__next__),
        ActionResolver(),
        ActionEventAdapter(
            world_id="demo-world",
            branch_id="main",
            world_revision=1,
            event_id_factory=lambda: "event-demo-1",
        ),
        WorldStateUpdater(),
        WorldStateApplier(),
        MemoryUpdater(memory_id_factory=lambda: "memory-event-1"),
        RelationshipUpdater(),
        AgentStateUpdater(),
        context_builder,
    )

    result = tick.run(agent_context, world_state, "发现受伤的病人，需要救助")

    print("原始世界状态:", world_state)
    print("生成事件:", result.events)
    print("新世界状态:", dict(result.world_state))
    print("新增记忆:", result.agent_context.memories[len(agent_context.memories):])
    print("新关系:", result.agent_context.relationships)
    print("新动态状态:", result.agent_context.dynamic_state)
    return {
        "initial_context": agent_context,
        "initial_world_state": world_state,
        "result": result,
    }


if __name__ == "__main__":
    run_demo()
