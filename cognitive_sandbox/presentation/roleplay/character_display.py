from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class CharacterDisplay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.character_name = QLabel("", self)
        self.character_name.setObjectName("characterDisplayName")
        self.portrait = QLabel("", self)
        self.portrait.setObjectName("characterPortrait")
        layout.addWidget(self.portrait)
        layout.addWidget(self.character_name)
