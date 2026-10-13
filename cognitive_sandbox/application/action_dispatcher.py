from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping, Iterable

from cognitive_sandbox.domain.action_intent import ActionIntent


@dataclass(frozen=True)
class ActionDispatchDecision:
    accepted: bool
    simulation_intent: str | None
    reason: str


class ActionDispatcher:
    """Validate a parsed intent and route only supported actions to the current simulation."""

    _ROUTES = {"observe": "observe", "look": "observe", "help": "help", "protect": "protect"}

    def dispatch(
        self,
        action: ActionIntent,
        *,
        known_entities: Iterable[str] | None = None,
        known_objects: Iterable[str] | None = None,
    ) -> ActionDispatchDecision:
        if not isinstance(action, ActionIntent):
            raise TypeError("action must be an ActionIntent.")
        entities = None if known_entities is None else {item.casefold() for item in known_entities if isinstance(item, str)}
        objects = None if known_objects is None else {item.casefold() for item in known_objects if isinstance(item, str)}

        if action.target is not None and entities is not None and action.target.casefold() not in entities:
            return ActionDispatchDecision(False, None, "目标不在当前已知人物中。")
        if action.object is not None and objects is not None and action.object.casefold() not in objects:
            return ActionDispatchDecision(False, None, "目标物品或地点当前不可确认。")

        route = self._ROUTES.get(action.intent)
        if route is None:
            return ActionDispatchDecision(
                False, None,
                "这个行动目前无法直接执行。你可以先观察环境、前往已知地点，或尝试与附近人物交谈。",
            )
        return ActionDispatchDecision(True, route, "已交由现有模拟规则判断。")
