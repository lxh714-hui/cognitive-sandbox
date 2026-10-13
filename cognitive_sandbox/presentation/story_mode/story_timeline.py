from PySide6.QtWidgets import QPushButton, QVBoxLayout, QWidget

from cognitive_sandbox.presentation.debug.narrative_replay import NarrativeReplay


class StoryTimeline(QWidget):
    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.replay = NarrativeReplay(session, parent=self)
        self.advance_button = QPushButton("世界继续一天", self)
        self.advance_button.setObjectName("storyAdvanceDayButton")
        layout = QVBoxLayout(self)
        layout.addWidget(self.replay)
        layout.addWidget(self.advance_button)

    def refresh(self):
        return self.replay.refresh()
