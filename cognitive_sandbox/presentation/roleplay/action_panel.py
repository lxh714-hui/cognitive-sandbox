from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget


class ActionPanel(QWidget):
    action_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("roleplayActionPanel")
        layout = QHBoxLayout(self)
        for label, action in (("执行", "execute"), ("等待", "wait"), ("观察", "observe")):
            button = QPushButton(label, self)
            button.setObjectName(f"roleplayAction_{action}")
            button.clicked.connect(lambda _=False, value=action: self.action_requested.emit(value))
            layout.addWidget(button)
