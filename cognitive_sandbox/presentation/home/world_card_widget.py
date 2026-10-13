from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class WorldCardWidget(QFrame):
    def __init__(self, name, description, status="", parent=None):
        super().__init__(parent)
        self.setObjectName("worldCard")
        layout = QVBoxLayout(self)
        self.name_label = QLabel(name, self)
        self.name_label.setObjectName("worldCardName")
        self.description_label = QLabel(description, self)
        self.description_label.setWordWrap(True)
        self.status_label = QLabel(status, self)
        layout.addWidget(self.name_label)
        layout.addWidget(self.description_label)
        layout.addWidget(self.status_label)
