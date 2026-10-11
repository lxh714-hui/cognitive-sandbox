from __future__ import annotations

from typing import Protocol

from cognitive_sandbox.application.cognitive_runtime import CognitiveRuntime
from cognitive_sandbox.application.decision_runtime import DecisionRuntime
from cognitive_sandbox.application.observation_layer import ObservationRuntime
from cognitive_sandbox.domain.actions import ActionProposal
from cognitive_sandbox.domain.models import Agent
from cognitive_sandbox.domain.observations import PerceptionContext
from cognitive_sandbox.domain.world_events import WorldEvent


class AgentReader(Protocol):
    """Read an agent's identity and world membership for a runtime invocation."""

    def get_agent(self, agent_id: str) -> Agent | None: ...


class AgentRuntime:
    """Connect one committed event to one agent's perception, cognition, and decision."""

    def __init__(
        self,
        agent_reader: AgentReader,
        observation_runtime: ObservationRuntime,
        cognitive_runtime: CognitiveRuntime,
        decision_runtime: DecisionRuntime,
    ) -> None:
        self._agent_reader = agent_reader
        self._observation_runtime = observation_runtime
        self._cognitive_runtime = cognitive_runtime
        self._decision_runtime = decision_runtime

    def process_event(
        self,
        agent_id: str,
        world_event: WorldEvent,
        perception_context: PerceptionContext,
    ) -> ActionProposal | None:
        """Process a single event for one agent and return, but never execute, an action."""
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("agent_id must not be empty.")
        if not isinstance(world_event, WorldEvent):
            raise TypeError("world_event must be a WorldEvent.")
        if not isinstance(perception_context, PerceptionContext):
            raise TypeError("perception_context must be a PerceptionContext.")

        agent = self._agent_reader.get_agent(agent_id)
        if agent is None:
            raise LookupError(f"Agent not found: {agent_id}.")
        if not isinstance(agent, Agent) or agent.id != agent_id:
            raise ValueError("Agent reader returned a different or invalid agent.")

        observations = self._observation_runtime.generate_observation(
            agent,
            world_event,
            context=perception_context,
        )
        if not observations:
            return None

        for observation in observations:
            if observation.agent_id != agent_id:
                raise ValueError("Observation runtime returned another agent's observation.")
            self._cognitive_runtime.process_observation(observation)

        proposals = self._decision_runtime.generate_actions(agent_id)
        return proposals[0] if proposals else None
