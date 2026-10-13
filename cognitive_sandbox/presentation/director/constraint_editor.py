from PySide6.QtWidgets import QHBoxLayout, QListWidget, QLineEdit, QPushButton, QVBoxLayout, QWidget


class ConstraintEditor(QWidget):
    """Small editor for player-authored narrative preferences and boundaries."""

    def __init__(self, manager=None, parent=None):
        super().__init__(parent)
        self.manager = manager
        layout = QVBoxLayout(self)
        self.list_widget = QListWidget(self)
        self.list_widget.setObjectName("directorConstraintList")
        layout.addWidget(self.list_widget)
        row = QHBoxLayout()
        self.input = QLineEdit(self)
        self.input.setObjectName("directorConstraintInput")
        self.input.setPlaceholderText("希望、避免或禁止某种叙事方向")
        row.addWidget(self.input, 1)
        self.add_button = QPushButton("新增", self)
        self.edit_button = QPushButton("修改所选", self)
        self.remove_button = QPushButton("删除所选", self)
        row.addWidget(self.add_button)
        row.addWidget(self.edit_button)
        row.addWidget(self.remove_button)
        layout.addLayout(row)
        self.add_button.clicked.connect(self.add_constraint)
        self.edit_button.clicked.connect(self.edit_constraint)
        self.remove_button.clicked.connect(self.remove_constraint)
        self.list_widget.currentRowChanged.connect(self.load_selected)
        self.refresh()

    def set_manager(self, manager):
        self.manager = manager
        self.refresh()

    def refresh(self):
        self.list_widget.clear()
        for item in getattr(self.manager, "constraints", ()):
            label = {"PREFER": "希望", "AVOID": "避免", "FORBID": "禁止"}[item.constraint_type.value]
            self.list_widget.addItem(f"{label} · {item.intent.description} · {item.strength.value}")

    def add_constraint(self):
        text = self.input.text().strip()
        if self.manager is None or not text:
            return None
        result = self.manager.submit_text(text)
        self.input.clear()
        self.refresh()
        return result

    def edit_constraint(self):
        row = self.list_widget.currentRow()
        items = getattr(self.manager, "constraints", ())
        text = self.input.text().strip()
        if self.manager is None or not text or not 0 <= row < len(items):
            return False
        changed = self.manager.edit_constraint(items[row].id, text)
        self.refresh()
        return changed

    def remove_constraint(self):
        row = self.list_widget.currentRow()
        items = getattr(self.manager, "constraints", ())
        if self.manager is None or not 0 <= row < len(items):
            return False
        changed = self.manager.remove_constraint(items[row].id)
        self.refresh()
        return changed

    def load_selected(self, row):
        items = getattr(self.manager, "constraints", ())
        if 0 <= row < len(items):
            self.input.setText(items[row].intent.description)
