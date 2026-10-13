from __future__ import annotations

from uuid import uuid4

from cognitive_sandbox.domain.narrative_event import NarrativeEvent
from cognitive_sandbox.domain.roleplay_result import RoleplayResult
from cognitive_sandbox.domain.simulation_result import SimulationTickResult
from cognitive_sandbox.domain.world_events import WorldEvent


class GenericActionHandler:
    """Resolve a small set of grounded everyday actions without inventing facts."""

    _ACTIONS = {"wake", "eat", "work", "go_home", "move", "find", "inspect", "explore"}
    _DURATION = {"wake": 5, "eat": 20, "work": 60, "go_home": 15, "move": 15, "find": 10, "inspect": 5, "explore": 20}

    def __init__(self, *, id_factory=None):
        self._id_factory = id_factory or (lambda: uuid4().hex)

    @classmethod
    def supports(cls, intent):
        return isinstance(intent, str) and intent.casefold() in cls._ACTIONS

    def handle(self, action, context):
        intent = action.intent.casefold()
        state = dict(context.world_state)
        presence = context.presence_manager.get(action.actor_id) if context.presence_manager else None
        current_location = getattr(presence, "current_location", None) or state.get("location")
        destination = None

        if intent in {"move", "go_home", "explore"}:
            destination = self._destination(action, context, "move" if intent == "explore" else intent)
            if intent == "explore" and destination is None:
                state["player_activity"] = "exploring"
                description = f"你在{current_location or '附近'}放慢脚步，留意周围的动静。"
            elif destination is None:
                return self._failure(context, "当前没有可确认的目的地。你可以选择已知地点，或先观察周围。")
            else:
                current_location = destination.name
                state["location"] = destination.name
                state["player_activity"] = "exploring" if intent == "explore" else "traveling"
                if context.location_manager is not None:
                    context.location_manager.current_location_id = destination.location_id
                if presence is not None and presence.introduction_state.value in {"INTRODUCED", "ACTIVE"}:
                    context.presence_manager.move_to(action.actor_id, destination.name, travel_completed=True)
                description = f"你前往{destination.name}，开始留意周围的动静。" if intent == "explore" else f"你前往了{destination.name}。"
        elif intent == "find":
            target = self._find_character(action, context)
            if target is None:
                return self._failure(context, "目前无法确认目标人物的位置。你可以先在附近寻找，或补充人物姓名。")
            target_presence = context.presence_manager.get(target.character_id) if context.presence_manager else None
            if target_presence is None or target_presence.availability.value not in {"INTRODUCED", "ACTIVE"}:
                return self._failure(context, "目前还没有可靠线索表明这名人物就在附近。")
            state["player_activity"] = "looking_for_someone"
            description = f"你开始在{current_location or '附近'}寻找{target.character_state.name}。"
        else:
            if intent == "inspect" and action.object and not self._known_visible_object(action.object, state):
                return self._failure(context, "目前还无法确认这个物件就在眼前。你可以先观察周围，再检查看到的东西。")
            descriptions = {
                "wake": "你起身开始新的一天。",
                "eat": "你停下来吃了些东西，周围的时间也慢慢向前。",
                "work": "你投入了一段时间处理工作。",
                "inspect": f"你仔细查看了{action.object or '眼前可见的环境'}。",
            }
            state["player_activity"] = intent
            description = descriptions[intent]
            if intent == "work":
                state["work_status"] = "worked_recently"

        minutes = self._DURATION[intent]
        state["elapsed_minutes"] = state.get("elapsed_minutes", 0) + minutes
        clock = context.world_clock
        now = clock.advance(minutes) if clock is not None else None
        timestamp = now.isoformat() if now is not None else None
        if intent == "eat" and timestamp is not None:
            state["last_meal_time"] = timestamp
        event_id = f"event_{self._id_factory()}"
        event_type = "player_traveled" if intent in {"move", "go_home"} else "player_routine_action"
        event = WorldEvent(
            event_id, context.branch_id, context.world_id, event_type, action.actor_id,
            {"action_type": intent, "description": description, "minutes": minutes,
             "importance_level": 1 if intent in {"move", "find"} else 0},
            0, target_id=action.target, location=current_location if isinstance(current_location, str) else None,
            timestamp=timestamp,
            metadata={"description": description, "public_description": description,
                      "importance_level": 1 if intent in {"move", "find"} else 0},
        )
        events = [event]
        if clock is not None:
            events.append(WorldEvent(
                f"event_{self._id_factory()}", context.branch_id, context.world_id, "world_tick",
                action.actor_id, {"elapsed_minutes": minutes}, 0, timestamp=timestamp,
            ))
        result = SimulationTickResult(state, context.agent_context, tuple(events))
        narrative = NarrativeEvent(event_id, "行动", description, ())
        return RoleplayResult(context.turn.turn_id, True, (narrative,), (), result)

    @staticmethod
    def _known_visible_object(requested, state):
        query = requested.casefold().strip()
        for key in ("visible_objects", "objects_visible", "known_objects"):
            values = state.get(key, ())
            if not isinstance(values, (tuple, list, set, frozenset)):
                continue
            for value in values:
                names = (value.get("name"), value.get("object_id"), value.get("id")) if isinstance(value, dict) else (value,)
                if any(isinstance(name, str) and (query == name.casefold() or query in name.casefold())
                       for name in names):
                    return True
        return False

    def _destination(self, action, context, intent):
        manager = context.location_manager
        locations = tuple(getattr(manager, "locations", ())) if manager is not None else ()
        requested = action.object
        if intent == "go_home":
            return next((item for item in locations
                         if any(tag.casefold() in {"home", "house", "住所", "家"} for tag in item.tags)
                         or any(word in item.name for word in ("住所", "家"))), None)
        if not isinstance(requested, str) or not requested.strip():
            return None
        query = requested.casefold().strip()
        aliases = {"街上": ("街区", "附近街区", "neighborhood"), "街道": ("街区", "附近街区", "neighborhood"),
                   "便利店": ("便利店", "convenience_store")}
        candidates = (query, *aliases.get(query, ()))
        return next((item for item in locations
                     if any(candidate in {item.location_id.casefold(), item.name.casefold()}
                            or candidate in item.name.casefold() for candidate in candidates)), None)

    @staticmethod
    def _find_character(action, context):
        query = (action.target or "").casefold()
        if not query:
            return None
        return next((item for item in context.agent_contexts if item.character_id != action.actor_id and
                     query in {item.character_id.casefold(), item.character_state.name.casefold(),
                               item.character_state.role.casefold()}), None)

    @staticmethod
    def _failure(context, message):
        return RoleplayResult(context.turn.turn_id, False, (), (), system_message=message)
