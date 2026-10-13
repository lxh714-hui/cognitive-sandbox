from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QTextEdit


class IdentityEditorDialog(QDialog):
    """Edit a character's display identity through IdentityManager only."""

    def __init__(self, identity_manager, character_id, parent=None):
        super().__init__(parent)
        self.identity_manager = identity_manager
        self.character_id = character_id
        identity = identity_manager.get(character_id)
        if identity is None:
            raise KeyError(character_id)
        if not identity.editable:
            raise PermissionError("this character identity is fixed by its world package.")
        self.name_edit = QLineEdit(identity.display_name, self)
        self.description_edit = QTextEdit(identity.public_description, self)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QFormLayout(self)
        layout.addRow("角色名称", self.name_edit)
        layout.addRow("公开简介", self.description_edit)
        layout.addRow(buttons)

    def apply_changes(self):
        self.identity_manager.rename_character(self.character_id, self.name_edit.text())
        return self.identity_manager.update_description(self.character_id, self.description_edit.toPlainText())

    def accept(self):
        self.apply_changes()
        super().accept()
