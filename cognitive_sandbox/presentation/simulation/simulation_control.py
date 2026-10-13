from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget


class SimulationControl(QWidget):
    requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        for label, action in (("暂停", "pause"), ("继续", "resume"), ("下一天", "next_day"), ("快速推进", "fast_forward")):
            button = QPushButton(label, self)
            button.setObjectName(f"simulationControl_{action}")
            button.clicked.connect(lambda _=False, value=action: self.requested.emit(value))
            layout.addWidget(button)
