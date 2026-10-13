from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout

from .director_panel import DirectorPanel


class DirectorDialog(QDialog):
    """Optional standalone host for the same DirectorPanel used by the main window."""

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.setWindowTitle("导演模式")
        self.resize(720, 480)
        layout = QVBoxLayout(self)
        self.panel = DirectorPanel(session, self)
        layout.addWidget(self.panel)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
