from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class CharacterProfilePanel(QWidget):
    """Read-only public identity profile; does not expose character control."""

    def __init__(self, identity, parent=None, *, encounter_manager=None, information_manager=None, character_id=None):
        super().__init__(parent)
        self.identity = identity
        self.encounter_manager = encounter_manager
        self.information_manager = information_manager
        self.character_id = character_id or getattr(identity, "character_id", None)
        self.name_label = QLabel(self)
        self.source_label = QLabel(self)
        self.description_label = QLabel(self)
        self.aliases_label = QLabel(self)
        self.encounters_label = QLabel(self)
        self.information_label = QLabel(self)
        layout = QVBoxLayout(self)
        for widget in (self.name_label, self.source_label, self.description_label, self.aliases_label,
                       self.encounters_label, self.information_label):
            layout.addWidget(widget)
        self.refresh()

    def refresh(self):
        self.name_label.setText(self.identity.display_name)
        self.source_label.setText(f"身份来源：{self.identity.naming_source}")
        self.description_label.setText(self.identity.public_description)
        self.aliases_label.setText("别名：" + "、".join(self.identity.aliases))
        if self.encounter_manager is None or not self.character_id:
            self.encounters_label.setText("最近接触：暂无记录")
        else:
            recent = self.encounter_manager.public_recent_for(self.character_id, limit=5)
            lines = [f"{item['name']} · {item['location']} · { _familiarity_label(item['familiarity'])} · "
                     f"共同接触 {item['shared_experience_count']} 次" for item in recent]
            self.encounters_label.setText("最近接触：" + ("；".join(lines) if lines else "暂无记录"))
        if self.information_manager is None or not self.character_id:
            self.information_label.setText("最近线索：暂无记录")
        else:
            recent_clues = self.information_manager.public_recent_for(self.character_id, limit=3)
            self.information_label.setText("最近线索：" + ("；".join(
                f"{item['content']}（来源：{item['source']}）" for item in recent_clues
            ) if recent_clues else "暂无记录"))
        return self.identity


def _familiarity_label(value):
    if value >= .35:
        return "认识程度：熟悉"
    if value >= .12:
        return "认识程度：认识"
    return "认识程度：初次接触"
