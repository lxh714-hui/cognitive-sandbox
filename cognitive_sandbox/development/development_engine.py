from __future__ import annotations

from dataclasses import replace

from cognitive_sandbox.development.character_development import CharacterDevelopment
from cognitive_sandbox.development.development_record import DevelopmentChangeType, DevelopmentRecord


class DevelopmentEngine:
    """Convert a character's own event experience into small, traceable durable tendencies."""

    def __init__(self, states=(), processed_event_ids=()):
        self._states = {item.character_id: item for item in states}
        self._processed_event_ids = set(processed_event_ids)

    @property
    def states(self):
        return dict(self._states)

    @property
    def processed_event_ids(self):
        return tuple(sorted(self._processed_event_ids))

    def get(self, character_id):
        return self._states.get(character_id, CharacterDevelopment(character_id))

    def handle_event(self, event, context=None):
        actor = getattr(event, "actor_id", "")
        if not actor:
            return ()
        if event.event_id in self._processed_event_ids:
            return ()
        self._processed_event_ids.add(event.event_id)
        event_type = event.event_type.casefold()
        payload = event.payload
        changes = []
        before = self.get(actor)
        behavior = dict(before.behavior_tendencies)
        cognitive = dict(before.cognitive_tendencies)
        emotion = dict(before.emotion_tendencies)
        beliefs = dict(before.belief_shifts)
        if event_type in {"anomaly_observed", "anomaly_discovered", "anomaly_investigated"}:
            old = beliefs.get("anomaly_exists", "no_evidence")
            new = "anomaly_may_exist"
            if old != new:
                beliefs["anomaly_exists"] = new
                changes.append(DevelopmentRecord(actor, event.event_id, DevelopmentChangeType.BELIEF_SHIFT,
                                                 old, new, "角色亲自观察到异常线索"))
            old_weight = cognitive.get("pattern_recognition", 0.0)
            cognitive["pattern_recognition"] = min(1.0, old_weight + .05)
            changes.append(DevelopmentRecord(actor, event.event_id, DevelopmentChangeType.COGNITIVE_TENDENCY,
                                             str(old_weight), str(cognitive["pattern_recognition"]),
                                             "亲历线索强化了寻找规律的倾向"))
            old_weight = behavior.get("investigate", 0.0)
            behavior["investigate"] = min(1.0, old_weight + .05)
            changes.append(DevelopmentRecord(actor, event.event_id, DevelopmentChangeType.BEHAVIOR_TENDENCY,
                                             str(old_weight), str(behavior["investigate"]),
                                             "亲历线索提高了后续调查倾向"))
            old_tendency = emotion.get("curiosity", 0.0)
            emotion["curiosity"] = min(1.0, old_tendency + .03)
            changes.append(DevelopmentRecord(actor, event.event_id, DevelopmentChangeType.EMOTION_TENDENCY,
                                             str(old_tendency), str(emotion["curiosity"]),
                                             "亲历线索略微强化了面对异常时的好奇倾向"))
        elif event_type in {"npc_investigated", "npc_observed"}:
            old_weight = behavior.get("investigate", 0.0)
            behavior["investigate"] = min(1.0, old_weight + .02)
            changes.append(DevelopmentRecord(actor, event.event_id, DevelopmentChangeType.BEHAVIOR_TENDENCY,
                                             str(old_weight), str(behavior["investigate"]),
                                             "角色反复采取调查行动"))
        if changes:
            self._states[actor] = replace(
                before, belief_shifts=tuple(sorted(beliefs.items())),
                cognitive_tendencies=tuple(sorted(cognitive.items())),
                emotion_tendencies=tuple(sorted(emotion.items())),
                behavior_tendencies=tuple(sorted(behavior.items())),
                records=(*before.records, *changes),
            )
        return tuple(changes)

    def restore(self, states, processed_event_ids=()):
        values = tuple(states.values()) if hasattr(states, "values") else tuple(states)
        if any(not isinstance(item, CharacterDevelopment) for item in values):
            raise TypeError("states must contain CharacterDevelopment values.")
        self._states = {item.character_id: item for item in values}
        self._processed_event_ids = set(processed_event_ids)
