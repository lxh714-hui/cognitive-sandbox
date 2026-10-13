from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class InformationInspector(QWidget):
    """Read-only debug view of clues and their recorded propagation paths."""
    def __init__(self, information_manager, parent=None):
        super().__init__(parent)
        self.information_manager = information_manager
        self.summary = QLabel(self)
        self.details = QLabel(self)
        layout = QVBoxLayout(self)
        layout.addWidget(self.summary)
        layout.addWidget(self.details)
        self.refresh()

    def refresh(self):
        clues = self.information_manager.clues
        rumors = self.information_manager.rumors
        paths = self.information_manager.paths
        self.summary.setText(f"线索：{len(clues)} · 传闻：{len(rumors)} · 传播路径：{len(paths)}")
        lines = []
        by_id = {item.clue_id: item for item in clues}
        for path in paths[-20:]:
            clue = by_id.get(path.clue_id)
            title = clue.content_type if clue else "线索"
            route = " → ".join(path.holders)
            lines.append(f"{title}｜{route}｜可靠度 {path.reliability:.2f}")
        self.details.setText("\n".join(lines) if lines else "暂无传播记录")
        return {"clue_count": len(clues), "rumor_count": len(rumors), "path_count": len(paths)}
