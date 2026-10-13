from __future__ import annotations

from dataclasses import dataclass, replace

from cognitive_sandbox.relationship.relationship_state import RelationshipState
from .relationship_event import RelationshipEvent, RelationshipEventType
from .relationship_memory import RelationshipMemory
from .relationship_stage import RelationshipStage
from .relationship_transition import RelationshipDynamics, RelationshipTransition


@dataclass(frozen=True)
class RelationshipStageEntry:
    character_a: str
    character_b: str
    stage: RelationshipStage

    def __post_init__(self):
        if not self.character_a or not self.character_b or self.character_a == self.character_b:
            raise ValueError("stage entry requires two distinct character IDs.")
        if not isinstance(self.stage, RelationshipStage):
            object.__setattr__(self, "stage", RelationshipStage(self.stage))


@dataclass(frozen=True)
class RelationshipLifecycleSnapshot:
    stages: tuple[RelationshipStageEntry, ...] = ()
    dynamics: tuple[RelationshipDynamics, ...] = ()
    memories: tuple[RelationshipMemory, ...] = ()
    events: tuple[RelationshipEvent, ...] = ()
    transitions: tuple[RelationshipTransition, ...] = ()
    processed_event_ids: tuple[str, ...] = ()
    belief_adjusted_pairs: tuple[tuple[str, str], ...] = ()

    def __post_init__(self):
        for name, model in (("stages", RelationshipStageEntry), ("dynamics", RelationshipDynamics),
                            ("memories", RelationshipMemory), ("events", RelationshipEvent),
                            ("transitions", RelationshipTransition)):
            values = tuple(getattr(self, name))
            if any(not isinstance(item, model) for item in values):
                raise TypeError(f"{name} must contain {model.__name__} values.")
            object.__setattr__(self, name, values)
        processed = tuple(self.processed_event_ids)
        if any(not isinstance(item, str) or not item.strip() for item in processed):
            raise ValueError("processed_event_ids must contain non-empty strings.")
        object.__setattr__(self, "processed_event_ids", processed)
        pairs = tuple(tuple(pair) for pair in self.belief_adjusted_pairs)
        if any(len(pair) != 2 or any(not isinstance(item, str) or not item.strip() for item in pair) for pair in pairs):
            raise ValueError("belief_adjusted_pairs must contain character ID pairs.")
        object.__setattr__(self, "belief_adjusted_pairs", pairs)


class RelationshipLifecycleManager:
    """Track source-backed relationship events, dynamics, stages, and history.

    Numeric trust/respect/fear/affinity/hostility remain owned by the existing
    RelationshipManager. This layer records familiarity/dependence/distance and
    stage transitions without replacing that model.
    """

    _EVENTS = {
        "help_attempt": RelationshipEventType.HELP,
        "player_helped": RelationshipEventType.HELP,
        "protect_attempt": RelationshipEventType.PROTECT,
        "player_protected": RelationshipEventType.PROTECT,
        "npc_protected": RelationshipEventType.PROTECT,
        "player_lied": RelationshipEventType.BETRAY,
        "lied": RelationshipEventType.BETRAY,
        "betrayal": RelationshipEventType.BETRAY,
        "information_shared": RelationshipEventType.SHARE_INFORMATION,
        "share_information": RelationshipEventType.SHARE_INFORMATION,
        "knowledge_shared": RelationshipEventType.SHARE_INFORMATION,
        "argue": RelationshipEventType.ARGUE,
        "argument": RelationshipEventType.ARGUE,
        "npc_argued": RelationshipEventType.ARGUE,
        "cooperation": RelationshipEventType.COOPERATE,
        "cooperative_action": RelationshipEventType.COOPERATE,
        "shared_investigation": RelationshipEventType.COOPERATE,
        "npc_shared_investigation": RelationshipEventType.COOPERATE,
        "dialogue_event": RelationshipEventType.OBSERVE,
        "talk_attempt": RelationshipEventType.OBSERVE,
        "social_encounter": RelationshipEventType.OBSERVE,
    }
    _BASE_HANDLED = frozenset({
        "help_attempt", "player_helped", "protect_attempt",
        "player_lied", "lied", "player_threatened", "weapon_threat", "weapon_drawn", "weapon_draw",
    })

    def __init__(self, relationship_manager, *, character_ids=(), emotion_engine=None,
                 cognitive_engine=None, snapshot: RelationshipLifecycleSnapshot | None = None):
        self.relationship_manager = relationship_manager
        self.emotion_engine = emotion_engine
        self.cognitive_engine = cognitive_engine
        snapshot = snapshot or RelationshipLifecycleSnapshot()
        if not isinstance(snapshot, RelationshipLifecycleSnapshot):
            raise TypeError("snapshot must be a RelationshipLifecycleSnapshot.")
        self._stages = {(item.character_a, item.character_b): item.stage for item in snapshot.stages}
        self._dynamics = {(item.character_a, item.character_b): item for item in snapshot.dynamics}
        self._memories = list(snapshot.memories)
        self._events = list(snapshot.events)
        self._transitions = list(snapshot.transitions)
        self._processed = set(snapshot.processed_event_ids)
        self._belief_adjusted = set(snapshot.belief_adjusted_pairs)
        self.ensure_characters(character_ids)

    def ensure_characters(self, character_ids):
        ids = tuple(dict.fromkeys(item for item in character_ids if isinstance(item, str) and item.strip()))
        for source in ids:
            for target in ids:
                if source != target:
                    self._stages.setdefault((source, target), RelationshipStage.STRANGER)
                    self._dynamics.setdefault((source, target), RelationshipDynamics(source, target))

    @property
    def memories(self):
        return tuple(self._memories)

    @property
    def events(self):
        return tuple(self._events)

    @property
    def transitions(self):
        return tuple(self._transitions)

    @property
    def stages(self):
        return tuple(RelationshipStageEntry(a, b, stage)
                     for (a, b), stage in sorted(self._stages.items()))

    @property
    def dynamics(self):
        return tuple(self._dynamics[key] for key in sorted(self._dynamics))

    def stage_for(self, character_a: str, character_b: str) -> RelationshipStage:
        if character_a == character_b:
            return RelationshipStage.UNKNOWN
        return self._stages.get((character_a, character_b), RelationshipStage.UNKNOWN)

    def dynamics_for(self, character_a: str, character_b: str) -> RelationshipDynamics:
        return self._dynamics.get((character_a, character_b), RelationshipDynamics(character_a, character_b))

    def snapshot(self) -> RelationshipLifecycleSnapshot:
        return RelationshipLifecycleSnapshot(
            self.stages, self.dynamics, self.memories, self.events, self.transitions,
            tuple(sorted(self._processed)), tuple(sorted(self._belief_adjusted)),
        )

    def handle_event(self, event, context=None):
        if event.event_id in self._processed:
            return ()
        self._processed.add(event.event_id)
        kind = self._EVENTS.get(event.event_type)
        if kind is None:
            return ()
        target = event.target_id or event.payload.get("target_id")
        if not isinstance(target, str) or not target.strip() or target == event.actor_id:
            return ()
        # Information exchange must be explicit; ordinary dialogue does not
        # imply that a character disclosed protected knowledge.
        if kind is RelationshipEventType.SHARE_INFORMATION and event.payload.get("information_shared") is not True:
            return ()
        pair_directions = ((event.actor_id, target), (target, event.actor_id))
        made = []
        for source, other in pair_directions:
            self._stages.setdefault((source, other), RelationshipStage.STRANGER)
            self._dynamics.setdefault((source, other), RelationshipDynamics(source, other))
            relation_event = RelationshipEvent(
                f"{event.event_id}:{source}>{other}", source, other, kind,
                event.timestamp or "", event.event_id,
                {"world_event_type": event.event_type},
            )
            self._events.append(relation_event)
            delta = self._dynamics_delta(kind)
            old_dynamics = self._dynamics[(source, other)]
            self._dynamics[(source, other)] = replace(
                old_dynamics,
                familiarity=_bounded(old_dynamics.familiarity + delta[0]),
                dependence=_bounded(old_dynamics.dependence + delta[1]),
                distance=_bounded(old_dynamics.distance + delta[2]),
                shared_experience=old_dynamics.shared_experience + (1 if kind is RelationshipEventType.COOPERATE else 0),
            )
            numeric_impact = self._apply_additional_rule(source, other, kind, event)
            if kind in {RelationshipEventType.HELP, RelationshipEventType.PROTECT,
                        RelationshipEventType.SHARE_INFORMATION, RelationshipEventType.COOPERATE}:
                # Core RelationshipManager already applies its established
                # help/protect deltas; do not duplicate those values here.
                if kind in {RelationshipEventType.SHARE_INFORMATION, RelationshipEventType.COOPERATE}:
                    numeric_impact = numeric_impact or {"familiarity": delta[0]}
            elif kind is RelationshipEventType.ARGUE:
                numeric_impact = numeric_impact or {"conflict": 1}
            elif kind is RelationshipEventType.OBSERVE:
                numeric_impact = {"familiarity": delta[0]}
            self._memories.append(RelationshipMemory(
                source, other, event.event_id, kind.value.casefold(), numeric_impact or {"shared_experience": 1},
                event.timestamp or "",
            ))
            self._maybe_adjust_belief(source, other, event)
            if self._evaluate_stage(source, other, event):
                made.append(self._transitions[-1])
        return tuple(made)

    @staticmethod
    def _dynamics_delta(kind):
        return {
            RelationshipEventType.HELP: (.06, .02, -.04),
            RelationshipEventType.PROTECT: (.06, .03, -.05),
            RelationshipEventType.SHARE_INFORMATION: (.08, .02, -.06),
            RelationshipEventType.COOPERATE: (.08, .02, -.06),
            RelationshipEventType.ARGUE: (0, 0, .1),
            RelationshipEventType.BETRAY: (0, 0, .15),
            RelationshipEventType.OBSERVE: (.04, 0, -.02),
        }[kind]

    def _apply_additional_rule(self, source, target, kind, event):
        if event.event_type in self._BASE_HANDLED:
            return {"relationship_rule": "existing_relationship_manager"}
        deltas = {
            RelationshipEventType.BETRAY: {"trust": -25, "hostility": 10},
            RelationshipEventType.SHARE_INFORMATION: {"trust": 5, "respect": 2},
            RelationshipEventType.ARGUE: {"trust": -5, "hostility": 8},
            RelationshipEventType.COOPERATE: {"trust": 5, "respect": 5},
        }.get(kind)
        if not deltas:
            return {}
        old = self.relationship_manager.get_relationship(source, target)
        updated = replace(old, **{
            key: max(-100, min(100, getattr(old, key) + value)) for key, value in deltas.items()
        })
        self.relationship_manager.set_relationship(updated)
        if self.emotion_engine is not None:
            self.emotion_engine.relationship_changed(source, target, old, updated, event)
        return deltas

    def _evaluate_stage(self, source, target, event):
        key = (source, target)
        previous = self._stages.get(key, RelationshipStage.STRANGER)
        state = self.relationship_manager.get_relationship(source, target)
        dynamics = self._dynamics[key]
        if state.trust <= -60 and state.hostility >= 50:
            new, reason = RelationshipStage.BROKEN, "信任严重受损且敌意持续"
        elif state.hostility >= 25 or state.trust <= -25:
            new, reason = RelationshipStage.CONFLICTED, "敌意或信任损失达到冲突阈值"
        elif state.trust >= 75 and state.affinity >= 60 and dynamics.shared_experience >= 8:
            new, reason = RelationshipStage.CLOSE, "长期互信并积累共同经历"
        elif state.trust >= 60 and dynamics.shared_experience >= 5:
            new, reason = RelationshipStage.TRUSTED, "多次合作并建立稳定信任"
        elif dynamics.shared_experience >= 3 and state.trust >= 15:
            new, reason = RelationshipStage.COOPERATIVE, "共同经历达到合作阶段"
        elif dynamics.familiarity >= .35:
            new, reason = RelationshipStage.FAMILIAR, "多次接触提升了熟悉程度"
        elif dynamics.familiarity > 0:
            new, reason = RelationshipStage.ACQUAINTANCE, "发生了可追溯的初次接触"
        else:
            new, reason = previous, "没有新的阶段变化"
        if new is previous:
            return False
        self._stages[key] = new
        self._transitions.append(RelationshipTransition(
            source, target, previous, new, event.event_id, reason, event.timestamp or "",
        ))
        return True

    def _maybe_adjust_belief(self, owner, other, event):
        pair = (owner, other)
        if self.cognitive_engine is None or pair in self._belief_adjusted:
            return
        dynamics = self._dynamics[pair]
        if dynamics.shared_experience < 3 or self.relationship_manager.get_relationship(owner, other).trust < 15:
            return
        for belief in tuple(self.cognitive_engine.beliefs.get(owner, ())):
            text = belief.interpretation.casefold()
            if "他人不可信" not in text and "others are untrustworthy" not in text:
                continue
            from cognitive_sandbox.cognition.belief_inference import Belief
            updated = Belief(
                belief.source_fact,
                "\u5e76\u975e\u6240\u6709\u4eba\u90fd\u4e0d\u53ef\u4fe1\uff1b\u4e0e\u8fd9\u4e2a\u4eba\u7684\u5408\u4f5c\u7ecf\u5386\u63d0\u4f9b\u4e86\u53cd\u4f8b\u3002",
                max(0.0, belief.confidence - .1), belief.persistence, owner,
            )
            self.cognitive_engine.record_belief_change(owner, event.event_id, belief, updated)
            self._belief_adjusted.add(pair)
            break

    def action_score_modifier(self, owner_id, action):
        """A small deterministic preference from the owner's directed relationship."""
        target = getattr(action, "target", None)
        action_type = str(getattr(action, "action_type", "")).casefold()
        if isinstance(target, str) and target.strip():
            relation = self.relationship_manager.get_relationship(owner_id, target)
            dynamics = self.dynamics_for(owner_id, target)
            trust = relation.trust / 100
            respect = relation.respect / 100
            hostility = relation.hostility / 100
            if action_type in {"help", "protect", "socialize", "talk", "approach", "ask"}:
                return max(-.25, min(.25, .16 * trust + .08 * respect - .18 * hostility
                                     + .05 * dynamics.dependence - .05 * dynamics.distance))
            if action_type in {"avoid", "escape", "leave"}:
                return max(-.15, min(.15, .12 * hostility - .08 * trust))
        return 0.0


def _bounded(value):
    return max(0.0, min(1.0, float(value)))
