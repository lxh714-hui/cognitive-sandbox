from dataclasses import dataclass, replace
from datetime import datetime, timezone
import hashlib

from cognitive_sandbox.knowledge.models.knowledge_record import KnowledgeRecord, KnowledgeType
from cognitive_sandbox.knowledge.models.knowledge_source import KnowledgeSource
from cognitive_sandbox.knowledge.models.knowledge_visibility import KnowledgeVisibility
from cognitive_sandbox.knowledge.models.world_fact import WorldFact

from .clue import Clue
from .information_path import InformationPath
from .information_source import InformationSource, InformationSourceType
from .propagation_rule import PropagationRule
from .rumor import Rumor
from .rumor_network import RumorNetwork, RumorNetworkSnapshot


@dataclass(frozen=True)
class InformationSnapshot:
    network: RumorNetworkSnapshot = RumorNetworkSnapshot()
    sources: tuple[InformationSource, ...] = ()

    def __post_init__(self):
        if not isinstance(self.network, RumorNetworkSnapshot):
            raise TypeError("network must be RumorNetworkSnapshot")
        sources = tuple(self.sources)
        if any(not isinstance(item, InformationSource) for item in sources):
            raise TypeError("sources must contain InformationSource values")
        object.__setattr__(self, "sources", sources)


class InformationManager:
    """Deterministic, permission-scoped clue and rumor propagation service."""
    NON_INFORMATION_EVENTS = frozenset({"world_tick", "world_initialized", "information_received"})
    HIDDEN_MARKERS = frozenset({"hidden", "secret", "private", "true_cause", "hidden_world"})

    def __init__(self, *, knowledge_store, knowledge_retriever=None, authority_manager=None,
                 presence_manager=None, relationship_manager=None, agency_manager=None,
                 cognitive_engine=None, world_clock=None, rule=None,
                 snapshot: InformationSnapshot | RumorNetworkSnapshot | None = None):
        if not callable(getattr(knowledge_store, "add_fact", None)) or not callable(getattr(knowledge_store, "add_knowledge", None)):
            raise TypeError("knowledge_store must support add_fact and add_knowledge")
        self.knowledge_store = knowledge_store
        self.knowledge_retriever = knowledge_retriever
        self.authority_manager = authority_manager
        self.presence_manager = presence_manager
        self.relationship_manager = relationship_manager
        self.agency_manager = agency_manager
        self.cognitive_engine = cognitive_engine
        self.world_clock = world_clock
        self.rule = rule or PropagationRule()
        if isinstance(snapshot, InformationSnapshot):
            self._sources = list(snapshot.sources)
            snapshot = snapshot.network
        else:
            self._sources = []
        self.network = RumorNetwork(snapshot)
        self._pressure_callback = None

    def bind_narrative_pressure(self, callback):
        self._pressure_callback = callback

    @property
    def clues(self):
        return self.network.clues

    @property
    def rumors(self):
        return self.network.rumors

    @property
    def paths(self):
        return self.network.paths

    def snapshot(self):
        return InformationSnapshot(self.network.snapshot(), tuple(self._sources))

    def handle_event(self, event, context=None):
        if self.network.has_processed(event.event_id) or event.event_type in self.NON_INFORMATION_EVENTS:
            return ()
        self.network.mark_processed(event.event_id)
        if not self._is_public(event):
            return ()
        content = self._public_content(event)
        if not content:
            return ()
        now = event.timestamp or self._now()
        clue = Clue(
            clue_id=f"clue:{event.event_id}", source_event=event.event_id,
            content_type=str(event.event_type), reliability=self._reliability(event),
            visibility="public", location=event.location, created_time=now,
            content=content, related_entities=tuple(item for item in (event.actor_id, event.target_id) if item),
        )
        self.network.add_clue(clue)
        participants = tuple(dict.fromkeys(item for item in (event.actor_id, event.target_id) if item and item != "system"))
        holders: list[tuple[str, InformationSourceType, float, str]] = []
        for character_id in participants:
            if not self._permitted(character_id, public=True):
                continue
            source_kind = InformationSourceType.DIRECT_OBSERVATION
            text = content
            if self._store_for(character_id, clue, text, source_kind, clue.reliability, now, sender=None):
                holders.append((character_id, source_kind, clue.reliability, text))
                source = InformationSource(source_kind, clue.clue_id, "亲历事件形成的线索", character_id)
                self._sources.append(source)
                self.network.add_path(InformationPath(
                    clue.clue_id, (character_id,), clue.reliability, now, (source_kind.value,),
                ))

        # Only active characters at the event location can hear the first-hand report.
        # No location means no ambient spread; this avoids world-wide omniscience.
        for sender_id, _kind, sender_reliability, sender_text in tuple(holders):
            for receiver_id in self._nearby_characters(clue.location):
                if receiver_id == sender_id or receiver_id in participants or not self._permitted(receiver_id, public=True):
                    continue
                same_location = self._same_location(receiver_id, clue.location)
                relation = self.relationship_manager.get_relationship(sender_id, receiver_id) if self.relationship_manager else None
                trust = getattr(relation, "trust", 0.0)
                agency = getattr(self.agency_manager.get(receiver_id), "initiative", .5) if self.agency_manager else .5
                score = self.rule.score(same_location=same_location, trust=trust, agency=agency,
                                        reliability=sender_reliability, permission=True)
                if score < self.rule.minimum_score:
                    continue
                spread_count = 1 + sum(1 for item in self.network.rumors if item.origin_clue == clue.clue_id)
                reliability = max(0.0, min(1.0, sender_reliability - self.rule.reliability_decay * spread_count))
                distorted = self._distort(sender_text, clue.clue_id, sender_id, receiver_id, reliability, score)
                rumor_id = f"rumor:{clue.clue_id}:{sender_id}:{receiver_id}"
                rumor = Rumor(rumor_id, clue.clue_id, receiver_id, reliability,
                              min(1.0, self.rule.distortion_per_hop * spread_count + (1-score)*.1),
                              spread_count, distorted, sender_id)
                self.network.add_rumor(rumor)
                if self._store_for(receiver_id, clue, distorted, InformationSourceType.RUMOR,
                                   reliability, now, sender=sender_id):
                    self._sources.append(InformationSource(
                        InformationSourceType.RUMOR, rumor_id, "由角色转述的传闻", sender_id,
                    ))
                    self.network.add_path(InformationPath(
                        clue.clue_id, (sender_id, receiver_id), reliability, now,
                        (InformationSourceType.DIRECT_OBSERVATION.value, InformationSourceType.RUMOR.value),
                    ))
                    holders.append((receiver_id, InformationSourceType.RUMOR, reliability, distorted))
        if event.event_type in {"talk_attempt", "dialogue_event", "information_shared", "npc_report"}:
            # A conversation can carry earlier clues onward. The sender must
            # already hold that clue; merely being in the same world is not enough.
            for sender_id in participants:
                self._share_known_clues(sender_id, participants, clue.clue_id, now, event.location)
        # Existing paths must never be counted again on unrelated events.
        new_paths = tuple(path for path in self.network.paths
                          if path.clue_id == clue.clue_id)
        rumor_paths = tuple(path for path in new_paths if len(path.holders) > 1)
        if self._pressure_callback and rumor_paths:
            self._pressure_callback(clue, rumor_paths)
        return ()

    def received_for(self, character_id, limit=10):
        """Sanitized owner-only summary for profile presentation."""
        rows = []
        for record, _fact in self.knowledge_store.query(character_id):
            if record.source.source_type not in {"information", "rumor", "direct_observation"}:
                continue
            rows.append({"content": record.known_content, "source": record.source.description,
                         "reliability": record.confidence, "created_at": record.created_at,
                         "knowledge_type": record.knowledge_type.value})
        return tuple(rows[-max(0, int(limit)):])

    def public_recent_for(self, character_id, limit=5):
        return tuple({"content": row["content"], "source": row["source"]}
                     for row in self.received_for(character_id, limit))

    def _store_for(self, owner, clue, content, source_type, confidence, now, sender):
        fact_id = f"info:{clue.clue_id}:{owner}"
        if self.knowledge_store.get_fact(fact_id) is not None:
            return False
        fact = WorldFact(fact_id, content, "clue" if source_type is InformationSourceType.DIRECT_OBSERVATION else "rumor",
                         now, clue.related_entities, clue.reliability)
        self.knowledge_store.add_fact(fact)
        source = KnowledgeSource(
            source_id=clue.clue_id, source_type="rumor" if source_type is InformationSourceType.RUMOR else "information",
            description=(f"{sender} 转述的传闻" if sender else "亲历事件形成的线索"), actor_id=sender,
        )
        record = KnowledgeRecord(owner, fact_id,
                                 KnowledgeType.RUMOR if sender else KnowledgeType.OBSERVED,
                                 source, confidence, now, content,
                                 KnowledgeVisibility(allowed_character_ids=(owner,)))
        self.knowledge_store.add_knowledge(record)
        self._interpret(owner, clue, content, now)
        return True

    def _share_known_clues(self, sender_id, participants, new_clue_id, now, location):
        if not location:
            return
        known_facts = {record.fact_id for record, _ in self.knowledge_store.query(sender_id)
                       if record.source.source_type in {"information", "rumor"}}
        recipients = tuple(dict.fromkeys((*participants, *self._nearby_characters(location))))
        for clue in self.network.clues:
            if clue.clue_id == new_clue_id or f"info:{clue.clue_id}:{sender_id}" not in known_facts:
                continue
            for receiver_id in recipients:
                if receiver_id == sender_id or not self._permitted(receiver_id, public=True):
                    continue
                if not self._same_location(receiver_id, location):
                    continue
                relation = self.relationship_manager.get_relationship(sender_id, receiver_id) if self.relationship_manager else None
                trust = getattr(relation, "trust", 0.0)
                agency = getattr(self.agency_manager.get(receiver_id), "initiative", .5) if self.agency_manager else .5
                score = self.rule.score(same_location=True, trust=trust, agency=agency,
                                        reliability=clue.reliability, permission=True)
                if score < self.rule.minimum_score:
                    continue
                reliability = max(0.0, clue.reliability - self.rule.reliability_decay)
                content = self._distort(clue.content, clue.clue_id, sender_id, receiver_id, reliability, score)
                rumor_id = f"rumor:{clue.clue_id}:{sender_id}:{receiver_id}"
                rumor = Rumor(rumor_id, clue.clue_id, receiver_id, reliability,
                              min(1.0, self.rule.distortion_per_hop + (1-score)*.1),
                              1 + sum(item.origin_clue == clue.clue_id for item in self.network.rumors),
                              content, sender_id)
                if not self._store_for(receiver_id, clue, content, InformationSourceType.RUMOR,
                                       reliability, now, sender_id):
                    continue
                self.network.add_rumor(rumor)
                self._sources.append(InformationSource(InformationSourceType.RUMOR, rumor_id,
                                                       "由角色转述的旧线索", sender_id))
                prior = tuple(path for path in self.network.paths
                              if path.clue_id == clue.clue_id and path.holders[-1] == sender_id)
                prior = max(prior, key=lambda item: len(item.holders), default=None)
                holders = (*prior.holders, receiver_id) if prior else (sender_id, receiver_id)
                source_types = (*prior.source_types, InformationSourceType.RUMOR.value) if prior else (InformationSourceType.RUMOR.value,)
                self.network.add_path(InformationPath(clue.clue_id, holders, reliability, now, source_types))

    def _interpret(self, owner, clue, content, now):
        if self.cognitive_engine is None:
            return
        from cognitive_sandbox.domain.world_events import WorldEvent
        event = WorldEvent(f"information:{clue.clue_id}:{owner}", "main", "information", "information_received",
                           owner, {"description": content}, 0, location=clue.location, timestamp=now)
        thought = self.cognitive_engine.interpret_event(owner, event, (content,))
        infer = getattr(self.cognitive_engine, "infer_belief", None)
        if callable(infer):
            infer(owner, f"info:{clue.clue_id}:{owner}", thought.interpretation,
                  min(thought.confidence, clue.reliability), persistence=.4)

    def _nearby_characters(self, location):
        if self.presence_manager is None or not location:
            return ()
        from cognitive_sandbox.character_presence.character_presence import PresenceState
        return tuple(item.character_id for item in self.presence_manager.presences
                     if item.current_location == location and item.availability in {
                         PresenceState.INTRODUCED, PresenceState.ACTIVE
                     })

    def _same_location(self, character_id, location):
        if not location or self.presence_manager is None:
            return False
        presence = self.presence_manager.get(character_id)
        return bool(presence and presence.current_location == location)

    def _permitted(self, character_id, *, public):
        if self.authority_manager is None:
            return True
        authority = self.authority_manager.authority_for(character_id)
        return bool(authority and self.authority_manager.check_visibility_permission(
            character_id, character_id, "public" if public else "hidden_knowledge"))

    def _is_public(self, event):
        visibility = event.payload.get("visibility", "public")
        if visibility not in {"public", "visible", "local", "observed"}:
            return False
        if any(str(key).casefold() in self.HIDDEN_MARKERS for key in event.payload):
            return False
        if event.event_type.startswith(("director_", "information_")):
            return False
        return True

    @staticmethod
    def _public_content(event):
        metadata = event.metadata or {}
        content = metadata.get("public_description") or event.payload.get("public_description") or event.payload.get("description")
        if not isinstance(content, str) or not content.strip():
            return None
        return content.strip()

    @staticmethod
    def _reliability(event):
        value = event.payload.get("importance", .5)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            value = .5
        return max(.1, min(.95, float(value) if value else .5))

    def _now(self):
        return self.world_clock.current_time().isoformat() if self.world_clock else datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _distort(content, clue_id, sender, receiver, reliability, score):
        if reliability >= .75 and score >= .7:
            return f"听说：{content}"
        # Stable, deterministic loss of detail rather than an invented contrary claim.
        digest = hashlib.sha256(f"{clue_id}:{sender}:{receiver}".encode()).digest()[0]
        if digest % 2:
            return "附近似乎发生了一件值得留意的事。"
        return f"有人提到：{content}（细节未核实）"
