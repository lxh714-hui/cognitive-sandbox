from PySide6.QtWidgets import QListWidget
from datetime import datetime

from cognitive_sandbox.event.event_importance import event_importance_level
from cognitive_sandbox.presentation.debug.narrative_replay import _event_category, filter_story_events


class SimulationTimeline(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("simulationTimeline")

    def set_events(self, events, *, start_time=None, include_routine=False):
        self.clear()
        for event in filter_story_events(events, include_routine=include_routine):
            metadata = dict(getattr(event, "payload", {}) or {})
            metadata.update(getattr(event, "metadata", None) or {})
            if not isinstance(metadata, dict) and not hasattr(metadata, "get"):
                metadata = {}
            if metadata.get("visibility") in {"hidden", "private"}:
                continue
            if getattr(event, "event_type", "") == "world_tick":
                continue
            description = metadata.get("public_description") or metadata.get("description")
            if not isinstance(description, str) or not description.strip():
                continue
            timestamp = getattr(event, "timestamp", "")
            try:
                moment = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                start = datetime.fromisoformat(start_time.replace("Z", "+00:00")) if isinstance(start_time, str) else start_time
                day = max(1, (moment - start).days + 1) if isinstance(start, datetime) else moment.day
                clock = moment.strftime("%H:%M")
                shown_time = f"Day {day} {clock}"
            except (AttributeError, TypeError, ValueError):
                shown_time = ""
            category = _event_category(getattr(event, "event_type", ""))
            prefix = f"{shown_time} · " if shown_time else ""
            self.addItem(f"{prefix}{category} · {description}")
