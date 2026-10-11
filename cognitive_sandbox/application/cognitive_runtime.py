from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4

from cognitive_sandbox.domain.cognition import (
    AgentCognitiveState,
    Belief,
    CognitiveUpdateProposal,
    EmotionState,
    LongTermMemory,
    ProposalOperation,
    WorkingMemoryItem,
)
from cognitive_sandbox.domain.observations import ObservationRecord
from cognitive_sandbox.domain.world_events import WorldEvent


class CognitiveStateStore(Protocol):
    def get_world_event(self, event_id: str) -> WorldEvent | None: ...
    def get_cognitive_state(self, agent_id: str) -> AgentCognitiveState | None: ...
    def commit_cognitive_update(
        self, proposal: CognitiveUpdateProposal, state: AgentCognitiveState
    ) -> bool: ...


class CognitiveUpdateRejected(ValueError):
    """Raised when a proposal fails source, permission, version, or operation checks."""


class CognitiveRevisionConflict(CognitiveUpdateRejected):
    """Raised when the persisted agent state changed since a proposal was made."""


class CognitiveRuntime:
    """The only entry point for committing working-memory and emotion updates."""

    TARGET_LAYER = "agent_cognitive_state"
    BREAKING_PHRASES = ("broke object", "breaks object", "打碎", "摔碎", "破碎", "碎裂")

    def __init__(
        self,
        state_store: CognitiveStateStore,
        *,
        id_factory: Callable[[], str] | None = None,
        clock: Callable[[], str] | None = None,
        working_memory_limit: int = 20,
    ) -> None:
        if isinstance(working_memory_limit, bool) or not isinstance(working_memory_limit, int):
            raise TypeError("working_memory_limit must be an integer.")
        if working_memory_limit < 1:
            raise ValueError("working_memory_limit must be positive.")
        self._state_store = state_store
        self._id_factory = id_factory or (lambda: str(uuid4()))
        self._clock = clock or (lambda: datetime.now(timezone.utc).isoformat())
        self._working_memory_limit = working_memory_limit

    def get_state(self, agent_id: str) -> AgentCognitiveState:
        """Return a persisted immutable state, or the neutral initial state."""
        state = self._state_store.get_cognitive_state(agent_id)
        return state if state is not None else AgentCognitiveState(agent_id=agent_id)

    def process_observation(self, observation: ObservationRecord) -> AgentCognitiveState:
        """Create and submit a deterministic update proposal for one observation."""
        if not isinstance(observation, ObservationRecord):
            raise TypeError("observation must be an ObservationRecord.")
        state = self.get_state(observation.agent_id)
        source_events = self._validate_observation_sources(observation)
        proposal = CognitiveUpdateProposal(
            proposal_id=self._id_factory(),
            agent_id=observation.agent_id,
            target_layer=self.TARGET_LAYER,
            operation=(ProposalOperation.CREATE if state.cognitive_revision == 0 else ProposalOperation.UPDATE),
            source_refs=(observation.observation_id,),
            reason="Apply deterministic working-memory and emotion rules to an observation.",
            base_cognitive_revision=state.cognitive_revision,
            world_revision=max(event.world_revision for event in source_events),
        )
        return self.submit_proposal(proposal, observation)

    def activate_memory(self, memory: LongTermMemory) -> AgentCognitiveState:
        """Commit a retrieved, agent-owned memory as a working-memory activation."""
        if not isinstance(memory, LongTermMemory):
            raise TypeError("memory must be a LongTermMemory.")
        current = self.get_state(memory.agent_id)
        if any(item.content.get("memory_id") == memory.memory_id for item in current.working_memory):
            return current

        # The activation cites the memory's observation provenance. It does not read or
        # modify world events, and leaves the stored long-term memory untouched.
        source_world_revisions = [
            item.content.get("world_revision", 0) for item in current.working_memory
        ]
        world_revision = max(
            (revision for revision in source_world_revisions if isinstance(revision, int)),
            default=0,
        )
        proposal = CognitiveUpdateProposal(
            proposal_id=self._id_factory(),
            agent_id=memory.agent_id,
            target_layer=self.TARGET_LAYER,
            operation=ProposalOperation.ACTIVATE,
            source_refs=memory.source_refs,
            reason="Activate a retrieved long-term memory in working memory.",
            base_cognitive_revision=current.cognitive_revision,
            world_revision=world_revision,
        )
        item = WorkingMemoryItem(
            item_id=self._id_factory(),
            agent_id=memory.agent_id,
            content={
                "memory_id": memory.memory_id,
                "memory_type": memory.memory_type,
                "text": memory.content.get("text", ""),
                "activated": True,
            },
            source_refs=memory.source_refs,
            priority=memory.salience,
            created_at=self._clock(),
        )
        next_state = AgentCognitiveState(
            agent_id=current.agent_id,
            cognitive_revision=current.cognitive_revision + 1,
            working_memory=(*current.working_memory, item)[-self._working_memory_limit :],
            emotion_state=current.emotion_state,
            beliefs=current.beliefs,
        )
        if not self._state_store.commit_cognitive_update(proposal, next_state):
            raise CognitiveRevisionConflict("Persisted cognitive revision changed before activation.")
        return next_state

    def submit_proposal(
        self,
        proposal: CognitiveUpdateProposal,
        observation: ObservationRecord,
    ) -> AgentCognitiveState:
        """Validate a sourced proposal and atomically commit its derived state."""
        if not isinstance(proposal, CognitiveUpdateProposal):
            raise TypeError("proposal must be a CognitiveUpdateProposal.")
        if not isinstance(observation, ObservationRecord):
            raise TypeError("observation must be an ObservationRecord.")
        if proposal.agent_id != observation.agent_id:
            raise CognitiveUpdateRejected("Proposal agent must match the observation owner.")
        if proposal.target_layer != self.TARGET_LAYER:
            raise CognitiveUpdateRejected("Unsupported cognitive target layer.")
        current = self.get_state(proposal.agent_id)
        expected_operation = (
            ProposalOperation.CREATE if current.cognitive_revision == 0 else ProposalOperation.UPDATE
        )
        if proposal.operation is not expected_operation:
            raise CognitiveUpdateRejected("Proposal operation is not valid for the current state.")
        if proposal.base_cognitive_revision != current.cognitive_revision:
            raise CognitiveRevisionConflict("Proposal cognitive revision is stale.")
        if proposal.source_refs != (observation.observation_id,):
            raise CognitiveUpdateRejected("Proposal must cite the supplied observation record.")
        source_events = self._validate_observation_sources(observation)
        source_world_revision = max(event.world_revision for event in source_events)
        if proposal.world_revision != source_world_revision:
            raise CognitiveUpdateRejected("Proposal world revision does not match its sources.")

        next_state = self._derive_state(current, observation, source_events)
        if not self._state_store.commit_cognitive_update(proposal, next_state):
            raise CognitiveRevisionConflict("Persisted cognitive revision changed before commit.")
        return next_state

    def _validate_observation_sources(self, observation: ObservationRecord) -> list[WorldEvent]:
        events: list[WorldEvent] = []
        for source_id in observation.source_refs:
            event = self._state_store.get_world_event(source_id)
            if event is None:
                raise CognitiveUpdateRejected(f"Observation source is not committed: {source_id}.")
            events.append(event)
        if not events:
            raise CognitiveUpdateRejected("Observation has no committed world-event source.")
        if len({(event.world_id, event.branch_id) for event in events}) != 1:
            raise CognitiveUpdateRejected("Observation sources must belong to one world branch.")
        return events

    def _derive_state(
        self,
        current: AgentCognitiveState,
        observation: ObservationRecord,
        source_events: list[WorldEvent],
    ) -> AgentCognitiveState:
        now = self._clock()
        source_event = max(source_events, key=lambda event: event.world_revision)
        item = WorkingMemoryItem(
            item_id=self._id_factory(),
            agent_id=observation.agent_id,
            content={
                "observation_id": observation.observation_id,
                "text": observation.content,
                "channel": observation.channel,
                "uncertainty": observation.uncertainty,
                "source_event_ids": list(observation.source_refs),
                "world_id": source_event.world_id,
                "branch_id": source_event.branch_id,
                "world_revision": source_event.world_revision,
            },
            source_refs=(observation.observation_id,),
            priority=1.0 - observation.uncertainty,
            created_at=now,
        )
        emotion = self._update_emotion(current.emotion_state, observation, now)
        working_memory = (*current.working_memory, item)[-self._working_memory_limit :]
        has_source_belief = any(
            observation.observation_id in belief.source_refs for belief in current.beliefs
        )
        beliefs = current.beliefs
        if not has_source_belief:
            beliefs = (
                *beliefs,
                Belief(
                    belief_id=f"belief:{observation.agent_id}:{observation.observation_id}",
                    agent_id=observation.agent_id,
                    belief_type="perceptual",
                    proposition=observation.content,
                    confidence=1.0 - observation.uncertainty,
                    source_refs=(observation.observation_id,),
                ),
            )
        return AgentCognitiveState(
            agent_id=current.agent_id,
            cognitive_revision=current.cognitive_revision + 1,
            working_memory=working_memory,
            emotion_state=emotion,
            beliefs=beliefs,
        )

    @classmethod
    def _update_emotion(
        cls,
        current: EmotionState,
        observation: ObservationRecord,
        now: str,
    ) -> EmotionState:
        normalized = observation.content.casefold()
        if not any(phrase in normalized for phrase in cls.BREAKING_PHRASES):
            return current
        confidence = 1.0 - observation.uncertainty
        return EmotionState(
            valence=max(-1.0, current.valence - 0.2 * confidence),
            arousal=min(1.0, current.arousal + 0.25 * confidence),
            source_refs=(observation.observation_id,),
            updated_at=now,
        )
