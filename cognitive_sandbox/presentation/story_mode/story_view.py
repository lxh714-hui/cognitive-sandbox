from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from cognitive_sandbox.presentation.story_mode.story_timeline import StoryTimeline
from cognitive_sandbox.presentation.story_mode.conflict_view import ConflictView
from cognitive_sandbox.simulation_test.long_simulation_runner import LongSimulationRunner


class StoryView(QWidget):
    """Player-facing autonomous world viewer; no debug state or global facts are shown."""
    player_mode_requested = Signal()

    def __init__(self, session, parent=None, runner=None):
        super().__init__(parent)
        self.session = session
        self.runner = runner or LongSimulationRunner()
        name = getattr(session.scenario, "name", "世界")
        self.title = QLabel(name, self)
        self.title.setObjectName("storyWorldTitle")
        self.timeline = StoryTimeline(session, self)
        self.conflict_view = ConflictView(session, self)
        self.opportunity_summary = QLabel("", self)
        self.opportunity_summary.setObjectName("storyOpportunitySummary")
        self.player_choice = QPushButton("切换到玩家模式，以梁景身份行动", self)
        self.player_choice.setObjectName("storyPlayerModeChoice")
        layout = QVBoxLayout(self)
        layout.addWidget(self.title)
        layout.addWidget(self.timeline)
        layout.addWidget(self.opportunity_summary)
        layout.addWidget(self.conflict_view)
        layout.addWidget(self.player_choice)
        self.timeline.advance_button.clicked.connect(self.advance_day)
        self.player_choice.clicked.connect(self.player_mode_requested.emit)
        self._refresh_opportunities()

    def advance_day(self):
        self.runner.run_anchor(checkpoints=(1,), session=self.session, random_seed=0,
                               enable_player_idle=True)
        result = self.timeline.refresh()
        self.conflict_view.refresh()
        self._refresh_opportunities()
        return result

    def _refresh_opportunities(self):
        service = getattr(self.session, "opportunity_service", None)
        if service is None:
            self.opportunity_summary.setText("")
            return ()
        character_id = getattr(self.session, "player_character_id", self.session.player_id)
        opportunities = service.for_character(character_id, limit=3)
        self.opportunity_summary.setText("值得注意：\n" + "\n".join(
            item.description for item in opportunities if item.importance >= .65
        ) if any(item.importance >= .65 for item in opportunities) else "")
        return opportunities
