from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class ScenarioPresenter:
    """Turn trusted, player-visible scenario data into natural scene prose."""

    _LOCATION_KEYS = ("location", "current_location", "地点", "当前位置")
    _DESCRIPTION_KEYS = ("environment_description", "scene_description", "visible_description")

    def opening(self, session) -> str:
        content = getattr(session, "scenario_content", None)
        scenario = getattr(session, "scenario", None)
        world = getattr(content, "world_document", None) if content is not None else None
        state = self._world_state(session)
        world_name = self._text(getattr(world, "name", "")) or self._text(
            getattr(scenario, "name", "")
        )
        background = self._text(getattr(world, "description", "")) or self._text(
            getattr(scenario, "description", "")
        )
        location = self._first_text(state, self._LOCATION_KEYS)
        scene = self._scene_description(state, background, world_name, location)

        player = getattr(session, "agent_context", None)
        player_id = self._text(getattr(player, "character_id", ""))
        player_state = getattr(player, "character_state", None)
        player_card = next(
            (card for card in getattr(content, "character_cards", ()) if card.character_id == player_id),
            None,
        ) if content is not None else None
        player_background = self._text(getattr(player_card, "background", ""))
        player_name = self._text(getattr(player_card, "name", "")) or self._text(
            getattr(player_state, "name", "")
        )
        if player_name.casefold() in {player_id.casefold(), "玩家", "player"}:
            player_name = ""
        player_role = self._text(getattr(player_card, "occupation", "")) or self._text(
            getattr(player_state, "role", "")
        )
        if player_role.casefold() == player_id.casefold():
            player_role = ""
        identity = f"你叫{player_name}。" if player_name else "你以自己的身份踏入了这里。"
        if player_role:
            identity += f"你是{player_role}。"
        lines = []
        if player_name and player_background:
            clean_background = player_background.rstrip("。.!！?？")
            if clean_background.startswith(player_name):
                lines.append(clean_background + "。")
            else:
                lines.append(f"{player_name}{clean_background}。")
        else:
            lines.append(identity)
        if background and "关于" not in background and background not in scene:
            if world_name and world_name not in background:
                lines.append(f"《{world_name}》是{background.rstrip('。.!！?？')}。")
            else:
                lines.append(background)
        if location:
            if world_name:
                lines.append(f"《{world_name}》里，{player_name or '你'}重新回到了{location}。")
            else:
                lines.append(f"{player_name or '你'}重新回到了{location}。")
        lines.append(self._opening_environment(session, scene, location))
        lines.extend(self._visible_characters(session, state))
        details = self._grounded_opening_details(session, state, player_id)
        if details:
            lines.extend(details)
        else:
            notable = self._notable_location_detail(session, location)
            if notable:
                lines.append(notable)
        safe_lines = [line for line in lines if line and self._player_safe(line, session)]
        return " ".join(safe_lines)

    def _opening_environment(self, session, fallback: str, location: str) -> str:
        for item in getattr(session, "scenario_locations", ()):
            if not isinstance(item, Mapping):
                continue
            if item.get("name") == location:
                description = self._text(item.get("description", ""))
                if description and self._player_safe(description, session):
                    environment = description.split("，", 1)[0].rstrip("。")
                    return environment + "。" if environment else description
        return fallback

    def _notable_location_detail(self, session, location: str) -> str:
        for item in getattr(session, "scenario_locations", ()):
            if isinstance(item, Mapping) and item.get("name") == location:
                description = self._text(item.get("description", ""))
                if description and self._player_safe(description, session):
                    # Surface a concise, visible detail already stated by the location card.
                    detail = description.split("，")[-1].split("，")[-1].rstrip("。")
                    if detail and detail != description.rstrip("。"):
                        return f"有些细节值得留意：{detail}。"
                    return f"有些细节值得留意：{description}"
        return ""

    def observation(self, session) -> str:
        state = self._world_state(session)
        content = getattr(session, "scenario_content", None)
        world = getattr(content, "world_document", None) if content is not None else None
        world_name = self._text(getattr(world, "name", "")) or self._text(
            getattr(getattr(session, "scenario", None), "name", "")
        )
        location = self._first_text(state, self._LOCATION_KEYS)
        background = self._text(getattr(world, "description", ""))
        scene = self._scene_description(state, background, world_name, location)
        lines = ["你环顾四周。", scene]
        lines.extend(self._visible_characters(session, state))
        lines.extend(self._visible_objects(state))
        lines.extend(self._visible_events(session, state))
        player = getattr(session, "agent_context", None)
        player_id = self._text(getattr(player, "character_id", ""))
        for detail in self._grounded_opening_details(session, state, player_id):
            if detail not in lines:
                lines.append(detail)
        if len(lines) == 2 and not location and not self._first_text(state, self._DESCRIPTION_KEYS):
            lines[1] = "你身处一个陌生环境，周围的信息还需要进一步探索。"
        return "\n".join(line for line in lines if self._player_safe(line, session))

    @staticmethod
    def display_names(session) -> dict[str, str]:
        """Map known internal identifiers to player-facing names; unknown IDs are omitted."""
        names: dict[str, str] = {}
        content = getattr(session, "scenario_content", None)
        for card in getattr(content, "character_cards", ()) if content is not None else ():
            name = ScenarioPresenter._text(getattr(card, "name", ""))
            identifier = ScenarioPresenter._text(getattr(card, "character_id", ""))
            if identifier and name and name.casefold() != identifier.casefold():
                names[identifier] = name
        for context in getattr(session, "agent_contexts", ()):
            identifier = ScenarioPresenter._text(getattr(context, "character_id", ""))
            name = ScenarioPresenter._text(getattr(getattr(context, "character_state", None), "name", ""))
            if identifier and name and name.casefold() != identifier.casefold():
                names[identifier] = name
        return names

    def _scene_description(self, state, background: str, world_name: str, location: str) -> str:
        explicit = self._first_text(state, self._DESCRIPTION_KEYS)
        if explicit:
            return explicit
        if location:
            return f"你来到了{location}。"
        if background:
            return background
        return "你身处一个陌生环境，周围的信息还需要进一步探索。"

    def _grounded_opening_details(self, session, state, player_id: str) -> list[str]:
        # Runtime details are surfaced only when a scenario explicitly marks
        # them as visible prose; engine fields are never inferred into story text.
        values = state.get("visible_details", ())
        if isinstance(values, str):
            values = (values,)
        if not isinstance(values, (tuple, list, set, frozenset)):
            return []
        return [text for value in values if (text := self._text(value))
                and self._player_safe(text, session)]

    def _visible_characters(self, session, state) -> list[str]:
        names = self.display_names(session)
        visible = state.get("visible_characters", state.get("nearby_characters", ()))
        if isinstance(visible, (str, Mapping)) or not isinstance(visible, (tuple, list, set, frozenset)):
            visible = ()
        rendered = []
        for item in visible:
            if isinstance(item, Mapping):
                identifier = item.get("character_id", item.get("id"))
                supplied_name = self._text(item.get("name", ""))
                name = supplied_name if supplied_name and self._player_safe(supplied_name) else names.get(str(identifier), "")
                detail = self._text(item.get("description", ""))
            else:
                name = names.get(str(item), "")
                detail = ""
            if name:
                rendered.append(f"{name}{'，' + detail if detail else '在附近。'}")
        return rendered

    def _visible_objects(self, state) -> list[str]:
        values = state.get("visible_objects", state.get("objects_visible", ()))
        if isinstance(values, (str, Mapping)) or not isinstance(values, (tuple, list, set, frozenset)):
            return []
        lines = []
        for item in values:
            if isinstance(item, Mapping):
                name = self._text(item.get("name", ""))
                description = self._text(item.get("description", ""))
            else:
                name, description = self._text(item), ""
            if name:
                lines.append(f"你看到{name}{'：' + description if description else '。'}")
        return lines

    def _visible_events(self, session, state) -> list[str]:
        events = state.get("visible_events", state.get("current_events", ()))
        if isinstance(events, (str, Mapping)) or not isinstance(events, (tuple, list, set, frozenset)):
            return []
        lines = []
        for event in events:
            if isinstance(event, Mapping):
                description = self._text(event.get("description", event.get("name", "")))
            else:
                description = self._text(event)
            if description:
                lines.append(description)
        return lines

    @staticmethod
    def _world_state(session) -> Mapping[str, Any]:
        state = getattr(session, "world_state", {})
        return state if isinstance(state, Mapping) else {}

    @classmethod
    def _first_text(cls, state: Mapping[str, Any], keys) -> str:
        for key in keys:
            value = cls._text(state.get(key))
            if value and cls._player_safe(value):
                return value
        return ""

    @classmethod
    def _player_safe(cls, text: str, session=None) -> bool:
        lowered = text.casefold()
        forbidden = ("none", "未设置", "尚未设定", "information_level", "world_revision", "%")
        if any(token in lowered for token in forbidden):
            return False
        if session is not None:
            for internal_id in cls.display_names(session):
                if internal_id and internal_id.casefold() in lowered:
                    return False
        return True

    @staticmethod
    def _text(value: Any) -> str:
        return value.strip() if isinstance(value, str) else ""
