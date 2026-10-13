from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from .simulation_control import SimulationControl
from .simulation_timeline import SimulationTimeline
from cognitive_sandbox.event.event_importance import event_importance_level
from cognitive_sandbox.presentation.debug.narrative_replay import (
    NarrativeReplayEntry,
    _daily_summary,
    _event_category,
    filter_story_events,
)


class SimulationView(QWidget):
    player_mode_requested = Signal()

    def __init__(self, session=None, parent=None, runner=None):
        super().__init__(parent)
        self.session = session
        self.runner = runner
        self.paused = False
        self.day = 0
        self._summary_start = None
        if runner is None and session is not None:
            from tools.simulation_test.long_simulation_runner import LongSimulationRunner
            self.runner = LongSimulationRunner()
        layout = QVBoxLayout(self)
        self.date_label = QLabel("", self)
        self.summary = QLabel("故事正在等待模拟推进。", self)
        self.timeline = SimulationTimeline(self)
        self.controls = SimulationControl(self)
        self.player_button = QPushButton("切换到角色扮演", self)
        self.player_button.setObjectName("simulationToRoleplayButton")
        self.player_button.clicked.connect(self.player_mode_requested.emit)
        self.controls.requested.connect(self.handle_control)
        layout.addWidget(self.date_label)
        layout.addWidget(self.summary)
        layout.addWidget(self.timeline, 1)
        layout.addWidget(self.controls)
        layout.addWidget(self.player_button)
        self.refresh()

    def handle_control(self, action):
        if action == "pause":
            self.paused = True
            self.summary.setText("模拟已暂停。")
        elif action == "resume":
            self.paused = False
            self.summary.setText("模拟继续运行。")
        elif action == "next_day":
            return self.advance(1)
        elif action == "fast_forward":
            return self.advance(7)
        return None

    def advance(self, days):
        if self.paused or self.session is None or self.runner is None:
            return None
        result = self.runner.run_world(checkpoints=(days,), random_seed=self.day, session=self.session,
                                       enable_player_idle=True)
        self.day += days
        events = tuple(self.session.executor.event_timeline.events)
        self.timeline.set_events(events, start_time=self._story_start())
        self.date_label.setText(self.session.executor.world_clock.current_time().strftime("%Y年%m月%d日"))
        self.summary.setText(self._summary(events))
        return result

    def refresh(self):
        if self.session is None:
            self.date_label.setText("未选择世界")
            return ()
        self.date_label.setText(self.session.executor.world_clock.current_time().strftime("%Y年%m月%d日"))
        events = tuple(self.session.executor.event_timeline.events)
        self.timeline.set_events(events, start_time=self._story_start())
        self.summary.setText(self._summary(events))
        return events

    def _story_start(self):
        if self._summary_start is not None:
            return self._summary_start
        value = getattr(self.session, "scenario_started_at", None)
        if value:
            self._summary_start = value
        else:
            events = tuple(self.session.executor.event_timeline.events)
            self._summary_start = next((event.timestamp for event in events if event.timestamp), None)
        return self._summary_start

    def _summary(self, events):
        from datetime import datetime
        start_value = self._story_start()
        try:
            start = datetime.fromisoformat(start_value.replace("Z", "+00:00"))
        except (AttributeError, TypeError, ValueError):
            start = self.session.executor.world_clock.current_time()
        entries = []
        for event in filter_story_events(events):
            metadata = dict(event.payload)
            metadata.update(event.metadata or {})
            if event.event_type == "world_tick" or metadata.get("visibility") in {"hidden", "private"}:
                continue
            text = metadata.get("public_description") or metadata.get("description")
            if not isinstance(text, str) or not text.strip():
                continue
            try:
                timestamp = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
                day = max(1, (timestamp - start).days + 1)
            except (AttributeError, TypeError, ValueError):
                day = 1
            entries.append(NarrativeReplayEntry(
                event.timestamp or "", day, text, (), "event",
                event_importance_level(event), _event_category(event.event_type),
            ))
        return _daily_summary(entries)
