from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from .action_panel import ActionPanel
from .character_display import CharacterDisplay
from .dialogue_panel import DialoguePanel


class RoleplayView(QWidget):
    """Composed player-facing roleplay surface; no internal state inspector."""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.time_location = QLabel("", self)
        self.time_location.setObjectName("roleplayTimeLocation")
        self.character_display = CharacterDisplay(self)
        self.dialogue_panel = DialoguePanel(self)
        self.action_panel = ActionPanel(self)
        layout.addWidget(self.time_location)
        layout.addWidget(self.character_display)
        layout.addWidget(self.dialogue_panel, 1)
        layout.addWidget(self.action_panel)
