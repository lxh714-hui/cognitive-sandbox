from __future__ import annotations

from dataclasses import fields, is_dataclass
from enum import Enum
from collections.abc import Mapping
from typing import Any

from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.agent_state import AgentDynamicState
from cognitive_sandbox.domain.actions import ActionCandidate
from cognitive_sandbox.domain.character import CharacterState
from cognitive_sandbox.domain.character_card import CharacterCard, ExampleDialogue
from cognitive_sandbox.domain.character_mind import (
    CharacterMind, Identity, KnowledgeContext, MemoryContext, PersonalityProfile, RelationshipContext, SpeechStyle,
)
from cognitive_sandbox.domain.constraint import Constraint
from cognitive_sandbox.domain.event_card import EventCard
from cognitive_sandbox.domain.memory import InitialMemory
from cognitive_sandbox.domain.narrative_event import NarrativeEvent
from cognitive_sandbox.domain.patch_validation_result import PatchValidationResult, PatchValidationStatus
from cognitive_sandbox.domain.relationship import RelationshipState
from cognitive_sandbox.domain.roleplay_turn import RoleplayTurn
from cognitive_sandbox.domain.scenario import Scenario
from cognitive_sandbox.domain.scenario_content import ScenarioContent
from cognitive_sandbox.domain.world_document import WorldDocument
from cognitive_sandbox.domain.world_instance import WorldInstance
from cognitive_sandbox.domain.story import StoryBranch
from cognitive_sandbox.domain.world_events import WorldEvent
from cognitive_sandbox.domain.world_patch import CharacterAddition, WorldPatch, WorldPatchType
from cognitive_sandbox.history.world_event_record import WorldEventRecord
from cognitive_sandbox.history.world_memory import WorldDelta, WorldHistory, WorldHistoryRecord, WorldMemorySnapshot
from cognitive_sandbox.knowledge.models.knowledge_record import KnowledgeRecord, KnowledgeType
from cognitive_sandbox.knowledge.models.knowledge_source import KnowledgeSource
from cognitive_sandbox.knowledge.models.knowledge_visibility import KnowledgeVisibility
from cognitive_sandbox.knowledge.models.world_fact import WorldFact
from cognitive_sandbox.presentation.message import DisplayMessage, MessageType
from cognitive_sandbox.persistence.models.save_metadata import SaveMetadata
from cognitive_sandbox.relationship.relationship_state import RelationshipState as WorldRelationshipState
from cognitive_sandbox.relationship.lifecycle import (
    RelationshipDynamics, RelationshipEvent, RelationshipEventType, RelationshipLifecycleSnapshot,
    RelationshipMemory, RelationshipStage, RelationshipStageEntry, RelationshipTransition,
)
from cognitive_sandbox.goal.character_goal import CharacterGoal
from cognitive_sandbox.time.world_clock import WorldClockState
from cognitive_sandbox.time.time_scheduler import ScheduledWorldEvent
from cognitive_sandbox.world_evolution.state_change import StateChange
from cognitive_sandbox.world_evolution.resource_manager import WorldResource
from cognitive_sandbox.world_evolution.location_state import LocationState
from cognitive_sandbox.character_presence.character_presence import CharacterPresence, PresenceState
from cognitive_sandbox.character_presence.entry_rule import EntryRule
from cognitive_sandbox.motivation.character_motivation import CharacterMotivation
from cognitive_sandbox.narrative.narrative_thread import NarrativeThread, NarrativeThreadStatus
from cognitive_sandbox.narrative.narrative_state import NarrativeState
from cognitive_sandbox.narrative.conflict_detector import Conflict
from cognitive_sandbox.narrative.narrative_pressure import NarrativePressure
from cognitive_sandbox.narrative.event_planner import CandidateEvent
from cognitive_sandbox.narrative.narrative_anchor import NarrativeConstraint
from cognitive_sandbox.narrative.opportunity.narrative_opportunity import (
    NarrativeOpportunity, OpportunitySourceType, OpportunityStatus,
)
from cognitive_sandbox.emotion.emotional_state import EmotionalState
from cognitive_sandbox.emotion.emotion_event import EmotionEvent
from cognitive_sandbox.emotion.emotional_memory import EmotionalMemory
from cognitive_sandbox.director.director_intent import DirectorIntent, DirectorIntentType
from cognitive_sandbox.director.director_constraint import DirectorConstraint, DirectorConstraintStatus
from cognitive_sandbox.director.director_path_finder import DirectorPath
from cognitive_sandbox.director.director_result import DirectorResult
from cognitive_sandbox.director.constraint_type import ConstraintType
from cognitive_sandbox.director.constraint_target import ConstraintTarget
from cognitive_sandbox.director.constraint_strength import ConstraintStrength
from cognitive_sandbox.director.constraint_explanation import ConstraintExplanation
from cognitive_sandbox.authority.authority_level import AuthorityLevel
from cognitive_sandbox.authority.character_authority import CharacterAuthority
from cognitive_sandbox.cognition import (AttentionProfile, Belief, CognitiveMemory, CognitiveStyle,
                                          ReasoningProfile, ThoughtPattern)
from cognitive_sandbox.agency.character_agency import CharacterAgency
from cognitive_sandbox.agency.agency_state import AgencyState
from cognitive_sandbox.goal.lifecycle import (GoalLifecycleSnapshot, GoalState, GoalHistoryEntry,
                                               GoalTransition, GoalTransitionRule, GoalLifecycleState)
from cognitive_sandbox.development import CharacterDevelopment, DevelopmentRecord, DevelopmentChangeType
from cognitive_sandbox.identity import CharacterIdentity
from cognitive_sandbox.encounter import (
    CognitionCondition, EmotionCondition, EncounterCandidate, EncounterHistoryRecord, EncounterMemory,
    EncounterSnapshot, EncounterStatus, EncounterTrajectory, GoalCondition, LocationCondition,
    RelationshipCondition, TimeCondition,
)
from cognitive_sandbox.information import (
    Clue, InformationPath, InformationSnapshot, InformationSource, InformationSourceType,
    PropagationRule, Rumor, RumorNetworkSnapshot,
)
from cognitive_sandbox.conflict import (ConflictState, ConflictStatus, ConflictType, ConflictSnapshot,
                                        GoalPressure, ConflictParticipant, ConflictParticipantRole,
                                        ConflictResponseType, ConflictResponseCandidate,
                                        OppositionCandidate, OppositionSourceType)


_TYPES = {
    cls.__name__: cls for cls in (
        AgentContext, AgentDynamicState, CharacterState, CharacterCard, ExampleDialogue,
        CharacterMind, Identity, KnowledgeContext, MemoryContext, PersonalityProfile,
        RelationshipContext, SpeechStyle, Constraint, EventCard, InitialMemory, NarrativeEvent,
        ActionCandidate, StoryBranch, NarrativeOpportunity,
        PatchValidationResult, RelationshipState, RoleplayTurn, Scenario, ScenarioContent,
        WorldDocument, WorldInstance, CharacterAddition, WorldPatch, WorldEvent, KnowledgeRecord,
        KnowledgeSource, KnowledgeVisibility, WorldFact, DisplayMessage, SaveMetadata, WorldEventRecord,
        CharacterGoal, WorldClockState, ScheduledWorldEvent,
        StateChange, WorldResource, LocationState,
        CharacterPresence, EntryRule, CharacterMotivation, NarrativeThread, NarrativeState,
        Conflict, NarrativePressure, CandidateEvent, NarrativeConstraint,
        EmotionalState, EmotionEvent, EmotionalMemory,
        DirectorIntent, DirectorConstraint, DirectorPath, DirectorResult, ConstraintExplanation,
        CharacterAuthority,
        AttentionProfile, Belief, CognitiveMemory, CognitiveStyle, ReasoningProfile, ThoughtPattern,
        CharacterAgency, AgencyState,
        GoalLifecycleSnapshot, GoalState, GoalHistoryEntry, GoalTransition, GoalTransitionRule,
        CharacterDevelopment, DevelopmentRecord, CharacterIdentity,
        RelationshipDynamics, RelationshipEvent, RelationshipMemory, RelationshipLifecycleSnapshot,
        RelationshipStageEntry, RelationshipTransition,
        EncounterCandidate, EncounterTrajectory, EncounterSnapshot, EncounterMemory,
        EncounterHistoryRecord, LocationCondition, TimeCondition, GoalCondition,
        RelationshipCondition, EmotionCondition, CognitionCondition,
        Clue, InformationPath, InformationSnapshot, InformationSource, PropagationRule,
        Rumor, RumorNetworkSnapshot, WorldDelta, WorldHistoryRecord, WorldHistory, WorldMemorySnapshot,
        ConflictState, ConflictSnapshot, GoalPressure,
        ConflictParticipant, ConflictResponseCandidate, OppositionCandidate,
    )
}
_TYPES["WorldRelationshipState"] = WorldRelationshipState
_ENUMS = {
    cls.__name__: cls for cls in (
        PatchValidationStatus, WorldPatchType, KnowledgeType, MessageType, PresenceState, NarrativeThreadStatus,
        DirectorIntentType, DirectorConstraintStatus, ConstraintType, ConstraintTarget, ConstraintStrength,
        AuthorityLevel,
        GoalLifecycleState, DevelopmentChangeType,
        RelationshipStage, RelationshipEventType,
        EncounterStatus,
        InformationSourceType,
        OpportunitySourceType,
        OpportunityStatus,
        ConflictStatus, ConflictType,
        ConflictParticipantRole, ConflictResponseType, OppositionSourceType,
    )
}


class WorldSerializer:
    """Explicitly whitelisted serializer for saveable domain snapshots."""

    VERSION = 1
    _SENSITIVE_KEYS = frozenset({
        "api_key", "apikey", "token", "access_token", "refresh_token", "authorization",
    })

    def serialize_world(
        self,
        metadata: SaveMetadata,
        session,
        *,
        messages=(),
        patches=(),
        character_minds=None,
        knowledge_facts=(),
        knowledge_records=(),
        timeline=None,
        relationships=None,
    ) -> dict[str, Any]:
        if not isinstance(metadata, SaveMetadata):
            raise TypeError("metadata must be SaveMetadata.")
        required_session_fields = (
            "player_id", "agent_context", "agent_contexts", "world_state", "situation",
            "scenario", "scenario_content", "world_instance_id",
        )
        if session is None or any(not hasattr(session, name) for name in required_session_fields):
            raise TypeError("session must be a roleplay session.")
        executor = getattr(session, "executor", None)
        minds = character_minds
        if minds is None:
            minds = getattr(executor, "character_minds", {})
        if timeline is None:
            event_timeline = getattr(executor, "event_timeline", None)
            timeline = getattr(event_timeline, "events", ())
        if relationships is None:
            relationship_manager = getattr(executor, "relationship_manager", None)
            relationships = getattr(relationship_manager, "relationships", ())
        clock = getattr(executor, "world_clock", None)
        time_scheduler = getattr(executor, "time_scheduler", None)
        goal_manager = getattr(executor, "goal_manager", None)
        npc_scheduler = getattr(executor, "npc_scheduler", None)
        world_evolution = getattr(executor, "world_evolution_engine", None)
        resource_manager = getattr(executor, "resource_manager", None)
        location_manager = getattr(executor, "location_manager", None)
        autonomous = {
            "clock_state": getattr(clock, "state", None),
            "goals": tuple(getattr(goal_manager, "goals", ())),
            "pending_events": tuple(getattr(time_scheduler, "pending_events", ())),
            "state_changes": tuple(getattr(world_evolution, "state_changes", ())),
            "processed_evolution_event_ids": tuple(getattr(world_evolution, "processed_event_ids", ())),
            "resources": tuple(getattr(resource_manager, "resources", ())),
            "locations": tuple(getattr(location_manager, "locations", ())),
            "current_location_id": getattr(location_manager, "current_location_id", None),
            "scheduler_state": {
                "tick_count": getattr(time_scheduler, "tick_count", 0),
                "last_tick_id": getattr(npc_scheduler, "last_tick_id", None),
                "last_evaluated_tick": getattr(goal_manager, "last_evaluated_tick", None),
            },
            "agency_state": (
                npc_scheduler.agency_manager.snapshot()
                if npc_scheduler is not None and getattr(npc_scheduler, "agency_manager", None) is not None
                else AgencyState()
            ),
            "goal_lifecycle": getattr(getattr(npc_scheduler, "goal_lifecycle_manager", None), "snapshot", lambda: GoalLifecycleSnapshot())(),
            "goal_transition_rules": tuple(getattr(getattr(npc_scheduler, "goal_lifecycle_manager", None), "rules", ())),
            "development_states": tuple(getattr(getattr(session, "development_engine", None), "states", {}).values()),
            "development_processed_event_ids": tuple(getattr(getattr(session, "development_engine", None), "processed_event_ids", ())),
            "identities": tuple(getattr(getattr(session, "identity_manager", None), "identities", ())),
            "relationship_lifecycle": getattr(
                getattr(session, "relationship_lifecycle_manager", None), "snapshot",
                lambda: RelationshipLifecycleSnapshot(),
            )(),
            "encounters": getattr(
                getattr(session, "encounter_manager", None), "snapshot", lambda: EncounterSnapshot(),
            )(),
            "information": getattr(
                getattr(session, "information_manager", None), "snapshot", lambda: InformationSnapshot(),
            )(),
            "conflicts": getattr(
                getattr(session, "conflict_manager", None), "snapshot", lambda: ConflictSnapshot(),
            )(),
            "world_package": {
                "content_version": getattr(session, "anchor_content_version", None),
                "started_at": getattr(session, "anchor_started_at", None),
                "summary": {
                    "event_count": len(getattr(getattr(executor, "event_timeline", None), "events", ())),
                    "last_event_id": (getattr(executor.event_timeline, "events", ())[-1].event_id
                                      if getattr(getattr(executor, "event_timeline", None), "events", ()) else None),
                },
                "replay_index": len(getattr(getattr(executor, "event_timeline", None), "events", ())),
                "settings": dict(getattr(session, "anchor_world_settings", {})),
                "location_relations": getattr(session, "anchor_location_relations", ()),
                "routines": getattr(session, "anchor_routines", {}),
            },
        }
        payload = {
            "version": self.VERSION,
            "metadata": self._encode(metadata),
            "session": self._encode({
                "player_id": session.player_id,
                "agent_context": session.agent_context,
                "agent_contexts": tuple(session.agent_contexts),
                "target": session.target,
                "world_state": session.world_state,
                "situation": session.situation,
                "scenario": session.scenario,
                "scenario_content": session.scenario_content,
                "world_instance_id": session.world_instance_id,
                "player_character_id": getattr(session, "player_character_id", session.player_id),
            }),
            "messages": self._encode(tuple(messages)),
            "character_minds": self._encode(dict(minds or {})),
            "patches": self._encode(tuple(patches)),
            "knowledge": self._encode({
                "facts": tuple(knowledge_facts),
                "records": tuple(knowledge_records),
            }),
            "timeline": self._encode(tuple(timeline)),
            "world_memory": self._encode(getattr(
                getattr(session, "world_memory", None), "snapshot", lambda: WorldMemorySnapshot()
            )()),
            "relationships": self._encode(tuple(relationships)),
            "opportunities": self._encode(_opportunity_snapshot(session)),
            "world_tree": self._encode(getattr(
                getattr(getattr(session, "executor", None), "world_tree_manager", None),
                "snapshot", lambda: {},
            )()),
            "autonomous": self._encode(autonomous),
            "narrative": self._encode({
                "presence": tuple(getattr(getattr(session, "presence_manager", None), "presences", ())),
                "entry_rules": tuple(getattr(getattr(session, "presence_manager", None), "entry_rules", ())),
                "motivations": tuple(getattr(getattr(session, "motivation_manager", None), "motivations", ())),
                "state": getattr(session, "narrative_state", NarrativeState()),
                "constraints": tuple(getattr(session, "narrative_constraints", ())),
                "pressure": getattr(session, "narrative_pressure", None),
                "candidates": tuple(getattr(session, "candidate_events", ())),
                "opportunities": _opportunity_snapshot(session),
                "world_tree": getattr(
                    getattr(getattr(session, "executor", None), "world_tree_manager", None),
                    "snapshot", lambda: {},
                )(),
            }),
            "emotion": self._encode({
                "states": getattr(getattr(session, "emotion_engine", None), "states", {}),
                "history": tuple(getattr(getattr(session, "emotion_engine", None), "history", ())),
                "memories": tuple(getattr(getattr(session, "emotion_engine", None), "memories", ())),
            }),
            "director": self._encode({
                "constraints": tuple(getattr(getattr(session, "director_manager", None), "constraints", ())),
                "history": tuple(getattr(getattr(session, "director_manager", None), "history", ())),
            }),
            "authority": self._encode({
                "player_character_id": getattr(
                    getattr(session, "authority_manager", None), "player_character_id",
                    getattr(session, "player_character_id", session.player_id),
                ),
                "authorities": tuple(getattr(
                    getattr(session, "authority_manager", None), "authorities", {}
                ).values()),
            }),
            "cognition": self._encode({
                "styles": getattr(getattr(session, "executor", None).cognitive_engine, "styles", {})
                if getattr(getattr(session, "executor", None), "cognitive_engine", None) is not None else {},
                "reasoning_profiles": getattr(getattr(session, "executor", None).cognitive_engine, "reasoning_profiles", {})
                if getattr(getattr(session, "executor", None), "cognitive_engine", None) is not None else {},
                "attention_profiles": getattr(getattr(session, "executor", None).cognitive_engine, "attention_profiles", {})
                if getattr(getattr(session, "executor", None), "cognitive_engine", None) is not None else {},
                "beliefs": getattr(getattr(session, "executor", None).cognitive_engine, "beliefs", {})
                if getattr(getattr(session, "executor", None), "cognitive_engine", None) is not None else {},
                "memories": getattr(getattr(session, "executor", None).cognitive_engine, "memories", {})
                if getattr(getattr(session, "executor", None), "cognitive_engine", None) is not None else {},
                "thoughts": {key: tuple(value) for key, value in getattr(
                    getattr(getattr(session, "executor", None), "cognitive_engine", None), "thoughts", {}
                ).items()},
            }),
        }
        return payload

    def deserialize_world(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, Mapping):
            raise TypeError("save document must be a mapping.")
        if payload.get("version") != self.VERSION:
            raise ValueError("unsupported or missing world save version.")
        try:
            result = {
                "metadata": self._decode(payload["metadata"]),
                "session": self._decode(payload["session"]),
                "messages": self._decode(payload.get("messages", {"$tuple": []})),
                "character_minds": self._decode(payload.get("character_minds", {"$mapping": []})),
                "patches": self._decode(payload.get("patches", {"$tuple": []})),
                "knowledge": self._decode(payload.get("knowledge", {"$mapping": []})),
                "timeline": self._decode(payload.get("timeline", {"$tuple": []})),
                "world_memory": self._decode(payload.get(
                    "world_memory", self._encode(WorldMemorySnapshot(history=WorldHistory()))
                )),
                "relationships": self._decode(payload.get("relationships", {"$tuple": []})),
                "opportunities": self._decode(payload.get("opportunities", {"$tuple": []})),
                "world_tree": self._decode(payload.get("world_tree", {"$mapping": []})),
                "autonomous": self._decode(payload.get("autonomous", {"$mapping": []})),
                "narrative": self._decode(payload.get("narrative", {"$mapping": []})),
                "emotion": self._decode(payload.get("emotion", {"$mapping": []})),
                "director": self._decode(payload.get("director", {"$mapping": []})),
                "authority": self._decode(payload.get("authority", {"$mapping": []})),
                "cognition": self._decode(payload.get("cognition", {"$mapping": []})),
            }
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"invalid world save payload: {error}") from error
        if not isinstance(result["metadata"], SaveMetadata) or not isinstance(result["session"], dict):
            raise ValueError("world save is missing valid metadata or session state.")
        session = result["session"]
        session.setdefault("player_character_id", session.get("player_id"))
        if result["metadata"].instance_id != session.get("world_instance_id"):
            raise ValueError("world save instance identity does not match its session.")
        if not isinstance(session.get("agent_context"), AgentContext) or not isinstance(
            session.get("agent_contexts"), tuple
        ) or any(not isinstance(item, AgentContext) for item in session["agent_contexts"]):
            raise ValueError("world save contains invalid agent context state.")
        if not isinstance(session.get("world_state"), Mapping):
            raise ValueError("world save contains invalid world state.")
        if not isinstance(result["messages"], tuple) or any(
            not isinstance(item, DisplayMessage) for item in result["messages"]
        ):
            raise ValueError("world save contains invalid conversation history.")
        if not isinstance(result["patches"], tuple) or any(
            not isinstance(item, WorldPatch) for item in result["patches"]
        ):
            raise ValueError("world save contains invalid world patches.")
        if not isinstance(result["character_minds"], Mapping) or any(
            not isinstance(key, str) or not isinstance(mind, CharacterMind)
            for key, mind in result["character_minds"].items()
        ):
            raise ValueError("world save contains invalid character minds.")
        knowledge = result["knowledge"]
        if not isinstance(knowledge, Mapping) or not isinstance(knowledge.get("facts"), tuple) or any(
            not isinstance(item, WorldFact) for item in knowledge["facts"]
        ) or not isinstance(knowledge.get("records"), tuple) or any(
            not isinstance(item, KnowledgeRecord) for item in knowledge["records"]
        ):
            raise ValueError("world save contains invalid knowledge data.")
        if not isinstance(result["timeline"], tuple) or any(
            not isinstance(item, WorldEventRecord) for item in result["timeline"]
        ):
            raise ValueError("world save contains invalid event history.")
        if not isinstance(result["world_memory"], WorldMemorySnapshot):
            raise ValueError("world save contains invalid incremental world memory.")
        if not result["world_memory"].current_snapshot:
            result["world_memory"] = WorldMemorySnapshot(
                {"world_instance_id": session.get("world_instance_id"),
                 "world_state": session.get("world_state", {})},
                WorldHistory(),
            )
        if not isinstance(result["relationships"], tuple) or any(
            not isinstance(item, WorldRelationshipState) for item in result["relationships"]
        ):
            raise ValueError("world save contains invalid relationship data.")
        autonomous = result["autonomous"]
        if not isinstance(autonomous, Mapping):
            raise ValueError("world save contains invalid autonomous runtime state.")
        autonomous = dict(autonomous)
        autonomous.setdefault("clock_state", None)
        autonomous.setdefault("encounters", EncounterSnapshot())
        autonomous.setdefault("information", InformationSnapshot())
        autonomous.setdefault("conflicts", ConflictSnapshot())
        # Migrate saves written with the legacy package metadata key.
        if "world_package" not in autonomous:
            autonomous["world_package"] = autonomous.pop(
                "demo", {"content_version": None, "started_at": None,
                         "summary": {}, "replay_index": 0, "settings": {}}
            )
        autonomous.setdefault("goals", ())
        autonomous.setdefault("pending_events", ())
        autonomous.setdefault("state_changes", ())
        autonomous.setdefault("processed_evolution_event_ids", ())
        autonomous.setdefault("resources", ())
        autonomous.setdefault("locations", ())
        autonomous.setdefault("current_location_id", None)
        autonomous.setdefault("scheduler_state", {})
        autonomous.setdefault("agency_state", AgencyState())
        autonomous.setdefault("goal_lifecycle", GoalLifecycleSnapshot())
        autonomous.setdefault("goal_transition_rules", ())
        autonomous.setdefault("development_states", ())
        autonomous.setdefault("development_processed_event_ids", ())
        autonomous.setdefault("identities", ())
        autonomous.setdefault("relationship_lifecycle", RelationshipLifecycleSnapshot())
        if autonomous["clock_state"] is not None and not isinstance(autonomous["clock_state"], WorldClockState):
            raise ValueError("world save contains invalid clock state.")
        if not isinstance(autonomous["goals"], tuple) or any(not isinstance(item, CharacterGoal) for item in autonomous["goals"]):
            raise ValueError("world save contains invalid character goals.")
        if not isinstance(autonomous["pending_events"], tuple) or any(not isinstance(item, ScheduledWorldEvent) for item in autonomous["pending_events"]):
            raise ValueError("world save contains invalid scheduled events.")
        if not isinstance(autonomous["state_changes"], tuple) or any(not isinstance(item, StateChange) for item in autonomous["state_changes"]):
            raise ValueError("world save contains invalid state change history.")
        if any(not isinstance(item, str) or not item.strip() for item in autonomous["processed_evolution_event_ids"]):
            raise ValueError("world save contains invalid evolution event IDs.")
        if not isinstance(autonomous["resources"], tuple) or any(not isinstance(item, WorldResource) for item in autonomous["resources"]):
            raise ValueError("world save contains invalid world resources.")
        if not isinstance(autonomous["locations"], tuple) or any(not isinstance(item, LocationState) for item in autonomous["locations"]):
            raise ValueError("world save contains invalid location state.")
        if autonomous["current_location_id"] is not None and not isinstance(autonomous["current_location_id"], str):
            raise ValueError("world save contains an invalid current location ID.")
        if not isinstance(autonomous["scheduler_state"], Mapping):
            raise ValueError("world save contains invalid scheduler state.")
        if not isinstance(autonomous["agency_state"], AgencyState):
            raise ValueError("world save contains invalid agency state.")
        if not isinstance(autonomous["goal_lifecycle"], GoalLifecycleSnapshot):
            raise ValueError("world save contains invalid goal lifecycle state.")
        if not isinstance(autonomous["goal_transition_rules"], tuple) or any(not isinstance(item, GoalTransitionRule) for item in autonomous["goal_transition_rules"]):
            raise ValueError("world save contains invalid goal transition rules.")
        if not isinstance(autonomous["development_states"], tuple) or any(not isinstance(item, CharacterDevelopment) for item in autonomous["development_states"]):
            raise ValueError("world save contains invalid character development state.")
        if not isinstance(autonomous["development_processed_event_ids"], tuple) or any(
            not isinstance(item, str) or not item.strip() for item in autonomous["development_processed_event_ids"]
        ):
            raise ValueError("world save contains invalid development event IDs.")
        if not isinstance(autonomous["identities"], tuple) or any(not isinstance(item, CharacterIdentity) for item in autonomous["identities"]):
            raise ValueError("world save contains invalid character identity data.")
        if not isinstance(autonomous["relationship_lifecycle"], RelationshipLifecycleSnapshot):
            raise ValueError("world save contains invalid relationship lifecycle state.")
        if not isinstance(autonomous["information"], InformationSnapshot):
            raise ValueError("world save contains invalid information network state.")
        if not isinstance(autonomous["conflicts"], ConflictSnapshot):
            raise ValueError("world save contains invalid conflict state.")
        if not isinstance(autonomous["world_package"], Mapping):
            raise ValueError("world save contains invalid world package metadata.")
        result["autonomous"] = autonomous
        narrative = result["narrative"]
        if not isinstance(narrative, Mapping):
            raise ValueError("world save contains invalid narrative state.")
        narrative = dict(narrative)
        narrative.setdefault("presence", ())
        narrative.setdefault("entry_rules", ())
        narrative.setdefault("motivations", ())
        narrative.setdefault("state", NarrativeState())
        narrative.setdefault("constraints", ())
        narrative.setdefault("pressure", None)
        narrative.setdefault("candidates", ())
        narrative.setdefault("opportunities", result["opportunities"] or ())
        narrative.setdefault("world_tree", result["world_tree"] or {})
        result["opportunities"] = narrative["opportunities"]
        result["world_tree"] = narrative["world_tree"]
        if not isinstance(narrative["presence"], tuple) or any(not isinstance(item, CharacterPresence) for item in narrative["presence"]):
            raise ValueError("world save contains invalid character presence data.")
        if not isinstance(narrative["entry_rules"], tuple) or any(not isinstance(item, EntryRule) for item in narrative["entry_rules"]):
            raise ValueError("world save contains invalid character entry rules.")
        if not isinstance(narrative["motivations"], tuple) or any(not isinstance(item, CharacterMotivation) for item in narrative["motivations"]):
            raise ValueError("world save contains invalid motivation data.")
        if not isinstance(narrative["state"], NarrativeState):
            raise ValueError("world save contains invalid narrative thread state.")
        if not isinstance(narrative["constraints"], tuple) or any(not isinstance(item, NarrativeConstraint) for item in narrative["constraints"]):
            raise ValueError("world save contains invalid narrative constraints.")
        if narrative["pressure"] is not None and not isinstance(narrative["pressure"], NarrativePressure):
            raise ValueError("world save contains invalid narrative pressure.")
        if not isinstance(narrative["candidates"], tuple) or any(not isinstance(item, CandidateEvent) for item in narrative["candidates"]):
            raise ValueError("world save contains invalid narrative candidates.")
        if not isinstance(narrative["opportunities"], tuple) or any(
            not isinstance(item, NarrativeOpportunity) for item in narrative["opportunities"]
        ):
            raise ValueError("world save contains invalid narrative opportunities.")
        if not isinstance(narrative["world_tree"], Mapping):
            raise ValueError("world save contains invalid World Tree state.")
        branches = narrative["world_tree"].get("branches", ())
        if not isinstance(branches, tuple) or any(not isinstance(item, StoryBranch) for item in branches):
            raise ValueError("world save contains invalid World Tree branches.")
        result["narrative"] = narrative
        emotion = result["emotion"]
        if not isinstance(emotion, Mapping):
            raise ValueError("world save contains invalid emotional state.")
        emotion = dict(emotion)
        emotion.setdefault("states", {})
        emotion.setdefault("history", ())
        emotion.setdefault("memories", ())
        if not isinstance(emotion["states"], Mapping) or any(
            not isinstance(key, str) or not isinstance(value, EmotionalState)
            for key, value in emotion["states"].items()
        ):
            raise ValueError("world save contains invalid emotional states.")
        if not isinstance(emotion["history"], tuple) or any(
            not isinstance(item, EmotionEvent) for item in emotion["history"]
        ):
            raise ValueError("world save contains invalid emotion history.")
        if not isinstance(emotion["memories"], tuple) or any(
            not isinstance(item, tuple) or len(item) != 2 or not isinstance(item[0], str)
            or not isinstance(item[1], EmotionalMemory) for item in emotion["memories"]
        ):
            raise ValueError("world save contains invalid emotional memories.")
        result["emotion"] = emotion
        director = result["director"]
        if not isinstance(director, Mapping):
            raise ValueError("world save contains invalid director state.")
        director = dict(director)
        director.setdefault("constraints", ())
        director.setdefault("history", ())
        if not isinstance(director["constraints"], tuple) or any(
            not isinstance(item, DirectorConstraint) for item in director["constraints"]
        ):
            raise ValueError("world save contains invalid director constraints.")
        if not isinstance(director["history"], tuple) or any(
            not isinstance(item, DirectorResult) for item in director["history"]
        ):
            raise ValueError("world save contains invalid director history.")
        result["director"] = director
        authority = result["authority"]
        if not isinstance(authority, Mapping):
            authority = {}
        authority = dict(authority)
        authority.setdefault("player_character_id", session.get("player_character_id", session.get("player_id")))
        if not authority.get("authorities"):
            player_id = authority["player_character_id"]
            authority["authorities"] = tuple(
                CharacterAuthority.player(item.character_id)
                if item.character_id == player_id
                else CharacterAuthority.important_character(item.character_id)
                for item in session["agent_contexts"]
            )
        if not isinstance(authority["player_character_id"], str) or not authority["player_character_id"].strip():
            raise ValueError("world save contains invalid player character identity.")
        if not isinstance(authority["authorities"], tuple) or any(
            not isinstance(item, CharacterAuthority) for item in authority["authorities"]
        ):
            raise ValueError("world save contains invalid character authorities.")
        if sum(item.authority_level is AuthorityLevel.PLAYER for item in authority["authorities"]) != 1:
            raise ValueError("world save must contain exactly one Player Character authority.")
        if not any(item.character_id == authority["player_character_id"] and
                   item.authority_level is AuthorityLevel.PLAYER for item in authority["authorities"]):
            raise ValueError("world save player identity does not match its authority.")
        if session.get("player_character_id") != authority["player_character_id"]:
            raise ValueError("world save player identity does not match its session.")
        if result["metadata"].player_character_id not in (None, authority["player_character_id"]):
            raise ValueError("world save player identity does not match its metadata.")
        if result["metadata"].player_character_id is None:
            from dataclasses import replace
            result["metadata"] = replace(
                result["metadata"], player_character_id=authority["player_character_id"]
            )
        result["authority"] = authority
        cognition = result["cognition"]
        if not isinstance(cognition, Mapping):
            raise ValueError("world save contains invalid cognition state.")
        cognition = dict(cognition)
        for field in ("styles", "reasoning_profiles", "attention_profiles", "beliefs", "memories", "thoughts"):
            cognition.setdefault(field, {})
            if not isinstance(cognition[field], Mapping):
                raise ValueError(f"world save contains invalid cognitive {field}.")
        for key, value in cognition["styles"].items():
            if not isinstance(key, str) or not isinstance(value, CognitiveStyle):
                raise ValueError("world save contains invalid cognitive styles.")
        for key, value in cognition["reasoning_profiles"].items():
            if not isinstance(key, str) or not isinstance(value, ReasoningProfile):
                raise ValueError("world save contains invalid reasoning profiles.")
        for key, value in cognition["attention_profiles"].items():
            if not isinstance(key, str) or not isinstance(value, AttentionProfile):
                raise ValueError("world save contains invalid attention profiles.")
        for field, model in (("beliefs", Belief), ("memories", CognitiveMemory), ("thoughts", ThoughtPattern)):
            if any(not isinstance(key, str) or not isinstance(items, tuple)
                   or any(not isinstance(item, model) for item in items)
                   for key, items in cognition[field].items()):
                raise ValueError(f"world save contains invalid cognitive {field}.")
        result["cognition"] = cognition
        return result

    @classmethod
    def _encode(cls, value: Any) -> Any:
        if isinstance(value, Enum):
            enum_name = value.__class__.__name__
            if enum_name not in _ENUMS:
                raise TypeError(f"unsupported enum type: {enum_name}")
            return {"$enum": enum_name, "value": value.value}
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, Mapping):
            if any(not isinstance(key, str) for key in value):
                raise TypeError("saved mapping keys must be strings.")
            sensitive = [
                key for key in value
                if key.casefold() in cls._SENSITIVE_KEYS
                or key.casefold().endswith(("_api_key", "_token"))
            ]
            if sensitive:
                raise ValueError("save data contains a credential-like field.")
            return {"$mapping": [[key, cls._encode(item)] for key, item in value.items()]}
        if isinstance(value, (tuple, list)):
            return {"$tuple": [cls._encode(item) for item in value]}
        if isinstance(value, (set, frozenset)):
            return {"$frozenset": [cls._encode(item) for item in sorted(value, key=repr)]}
        if is_dataclass(value) and not isinstance(value, type):
            name = "WorldRelationshipState" if isinstance(value, WorldRelationshipState) else value.__class__.__name__
            if _TYPES.get(name) is not value.__class__:
                raise TypeError(f"unsupported saved model type: {name}")
            return {
                "$model": name,
                "fields": {field.name: cls._encode(getattr(value, field.name)) for field in fields(value)},
            }
        raise TypeError(f"unsupported save value: {type(value).__name__}")

    @classmethod
    def _decode(cls, value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, list):
            raise ValueError("untagged arrays are not valid save data.")
        if not isinstance(value, dict):
            raise ValueError("invalid encoded save value.")
        if "$enum" in value:
            enum_type = _ENUMS.get(value.get("$enum"))
            if enum_type is None:
                raise ValueError("save contains an unsupported enum.")
            return enum_type(value["value"])
        if "$tuple" in value:
            return tuple(cls._decode(item) for item in value["$tuple"])
        if "$frozenset" in value:
            return frozenset(cls._decode(item) for item in value["$frozenset"])
        if "$mapping" in value:
            pairs = value["$mapping"]
            if not isinstance(pairs, list):
                raise ValueError("invalid saved mapping.")
            result = {}
            for pair in pairs:
                if not isinstance(pair, list) or len(pair) != 2 or not isinstance(pair[0], str):
                    raise ValueError("invalid saved mapping entry.")
                if pair[0] in result:
                    raise ValueError("duplicate saved mapping key.")
                result[pair[0]] = cls._decode(pair[1])
            return result
        if "$model" in value:
            model_type = _TYPES.get(value.get("$model"))
            model_fields = value.get("fields")
            if model_type is None or not isinstance(model_fields, dict):
                raise ValueError("save contains an unsupported model.")
            return model_type(**{name: cls._decode(item) for name, item in model_fields.items()})
        raise ValueError("untagged object is not valid save data.")


def _opportunity_snapshot(session):
    service = getattr(session, "opportunity_service", None)
    manager = getattr(service, "manager", None)
    snapshot = getattr(manager, "snapshot", None)
    if callable(snapshot):
        return tuple(snapshot())
    # Do not call NarrativeOpportunityService.snapshot here: it refreshes and
    # evaluates new opportunities. Persistence reads stored state only.
    values = getattr(service, "opportunities", ())
    return tuple(values)
