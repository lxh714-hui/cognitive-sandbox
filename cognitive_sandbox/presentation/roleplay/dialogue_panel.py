from PySide6.QtWidgets import QTextBrowser, QVBoxLayout, QWidget


class DialoguePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.history = QTextBrowser(self)
        self.history.setObjectName("roleplayDialogueHistory")
        layout.addWidget(self.history)
