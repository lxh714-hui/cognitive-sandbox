from PySide6.QtWidgets import QLineEdit


class IntentInput(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("directorIntentInput")
        self.setPlaceholderText("希望世界向什么方向发展？")
