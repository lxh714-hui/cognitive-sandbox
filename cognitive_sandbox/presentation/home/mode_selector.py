from PySide6.QtWidgets import QComboBox


class ModeSelector(QComboBox):
    MODES = (("角色扮演", "roleplay"), ("模拟观察", "simulation"), ("导演模式", "director"))

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("homeModeSelector")
        for label, mode in self.MODES:
            self.addItem(label, mode)
