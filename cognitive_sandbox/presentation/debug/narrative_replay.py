from dataclasses import dataclass

from PySide6.QtWidgets import QCheckBox, QComboBox, QLabel, QTextBrowser, QVBoxLayout, QWidget
from cognitive_sandbox.event.event_importance import event_importance_level


def filter_story_events(events, *, include_routine=False):
    """Filter for the player-facing timeline while leaving the source history intact."""
    return tuple(event for event in events
                 if include_routine or event_importance_level(event) >= 1)


@dataclass(frozen=True)
class NarrativeReplayEntry:
    timestamp: str
    day: int
    text: str
    character_ids: tuple[str, ...] = ()
    source: str = "event"
    importance_level: int = 1
    category: str = "世界动态"


class NarrativeReplay(QWidget):
    """Read-only, character-scoped story timeline built from visible events and owned clues."""
    def __init__(self, session, character_id=None, parent=None):
        super().__init__(parent)
        self.session = session
        self.character_id = character_id or session.player_id
        self.view = QTextBrowser(self)
        self.view.setObjectName("narrativeReplayView")
        self.view.setReadOnly(True)
        self.filter = QComboBox(self)
        self.filter.setObjectName("narrativeReplayCharacterFilter")
        self.filter.addItem("玩家视角", session.player_id)
        for context in session.agent_contexts:
            if context.character_id != session.player_id:
                self.filter.addItem(self._name(context.character_id), context.character_id)
        index = self.filter.findData(self.character_id)
        self.filter.setCurrentIndex(max(0, index))
        self.filter.currentIndexChanged.connect(self._change_filter)
        self.status = QLabel(self)
        self.daily_summary = QLabel(self)
        self.daily_summary.setObjectName("narrativeDailySummary")
        self.daily_summary.setWordWrap(True)
        self.routine_toggle = QCheckBox("显示日常记录", self)
        self.routine_toggle.setObjectName("narrativeReplayRoutineToggle")
        self.routine_toggle.toggled.connect(lambda _checked: self.refresh())
        layout = QVBoxLayout(self)
        layout.addWidget(self.filter)
        layout.addWidget(self.status)
        layout.addWidget(self.daily_summary)
        layout.addWidget(self.routine_toggle)
        layout.addWidget(self.view)
        self.refresh()

    def _change_filter(self, _index):
        self.character_id = self.filter.currentData()
        self.refresh()

    def rows(self, *, include_routine=None):
        if include_routine is None:
            include_routine = self.routine_toggle.isChecked()
        executor = self.session.executor
        character_id = self.character_id
        knowledge = getattr(self.session, "knowledge_store", None)
        visible_event_ids = set()
        if knowledge is not None:
            for record, _fact in knowledge.query(character_id):
                fact_id = record.fact_id
                if fact_id.startswith("fact_"):
                    visible_event_ids.add(fact_id.removeprefix("fact_"))
                elif fact_id.startswith("info:clue:"):
                    visible_event_ids.add(fact_id.split(":", 2)[2].rsplit(":", 1)[0])
        from datetime import datetime
        start_value = getattr(self.session, "anchor_started_at", None)
        try:
            start = datetime.fromisoformat(start_value) if start_value else datetime.fromisoformat(executor.event_timeline.events[0].timestamp)
        except (ValueError, IndexError, AttributeError):
            start = executor.world_clock.current_time()
        entries = []
        visible_events = filter_story_events(executor.event_timeline.events, include_routine=include_routine)
        for event in visible_events:
            if event.event_type == "world_tick" or event.metadata.get("visibility") in {"hidden", "private"}:
                continue
            is_own = character_id in event.actor_ids or character_id in event.target_ids
            has_knowledge = event.event_id in visible_event_ids
            if not (is_own or has_knowledge):
                continue
            importance = event_importance_level(event)
            description = event.metadata.get("public_description") or event.metadata.get("description")
            if not isinstance(description, str) or not description.strip():
                description = _EVENT_TEXT.get(event.event_type)
            if not isinstance(description, str) or not description.strip():
                continue
            try:
                day = max(1, (datetime.fromisoformat(event.timestamp) - start).days + 1)
            except (TypeError, ValueError):
                day = 1
            entries.append(NarrativeReplayEntry(
                event.timestamp, day, description, (*event.actor_ids, *event.target_ids),
                "event", importance, _event_category(event.event_type),
            ))
        if knowledge is not None:
            for record, _fact in knowledge.query(character_id):
                if record.source.source_type not in {"information", "rumor"}:
                    continue
                try:
                    day = max(1, (datetime.fromisoformat(record.created_at) - start).days + 1)
                except (TypeError, ValueError):
                    day = 1
                entries.append(NarrativeReplayEntry(
                    record.created_at, day,
                    f"{record.known_content}（{record.source.description}，可信度 {record.confidence:.0%}）",
                    (character_id,), "information", 2, "线索与传闻",
                ))
        entries.sort(key=lambda row: row.timestamp)
        return tuple(entries)

    def refresh(self):
        now = self.session.executor.world_clock.current_time()
        location = getattr(self.session.presence_manager.get(self.character_id), "current_location", None)
        location_state = self.session.executor.location_manager.get(location) if location else None
        shown_location = getattr(location_state, "name", None) or ("住所" if self.character_id == self.session.player_id else "所在地点")
        self.status.setText(f"{now:%Y年%m月%d日} · {shown_location}")
        rows = self.rows()
        self.daily_summary.setText(_daily_summary(rows))
        self.view.setPlainText("\n\n".join(
            f"Day {row.day} {self._hour_minute(row.timestamp)}\n{row.text}" for row in rows
        ) or "故事刚刚开始。")
        return rows

    @staticmethod
    def _hour_minute(timestamp):
        try:
            from datetime import datetime
            return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).strftime("%H:%M")
        except (AttributeError, TypeError, ValueError):
            return "00:00"

    def _name(self, character_id):
        identity = getattr(self.session, "identity_manager", None)
        return identity.display_name_for(character_id, "角色") if identity else "角色"


_EVENT_TEXT = {
    "npc_investigated": "有人开始核实自己掌握的线索。",
    "npc_observed": "有人停下来观察周围。",
    "npc_socialized": "有人和附近的人交谈。",
    "social_encounter": "两人在同一地点有了接触。",
    "neighborhood_rumor": "街区里有人谈起一则尚未核实的消息。",
}


def _event_category(event_type):
    value = str(event_type).casefold()
    if any(token in value for token in ("conflict", "threat", "argue", "hostil")):
        return "冲突变化"
    if any(token in value for token in ("relationship", "trust", "encounter", "dialogue", "social")):
        return "关系与接触"
    if any(token in value for token in ("information", "rumor", "clue", "investigat")):
        return "线索与调查"
    if any(token in value for token in ("goal", "progress", "milestone")):
        return "目标变化"
    return "世界动态"


def _daily_summary(rows):
    rows = tuple(rows)
    if not rows:
        return "今天还没有新的重要进展。"
    latest_day = max(item.day for item in rows)
    latest = [item for item in rows if item.day == latest_day]
    grouped = {}
    for item in latest:
        grouped.setdefault(item.category, [])
        if item.text not in grouped[item.category]:
            grouped[item.category].append(item.text)
    fragments = [f"{category}：{'；'.join(texts[:2])}" for category, texts in grouped.items()]
    return f"Day {latest_day} 摘要：" + "　".join(fragments[:3])
