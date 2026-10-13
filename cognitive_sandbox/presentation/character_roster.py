from __future__ import annotations

from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QListWidget, QPushButton, QTextBrowser, QVBoxLayout

from cognitive_sandbox.authority.authority_level import AuthorityLevel


class CharacterRosterDialog(QDialog):
    """Player-facing character directory with read-only profile details."""

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.setWindowTitle("角色档案")
        self.setObjectName("characterRosterDialog")
        self.resize(620, 420)
        self.session = session
        layout = QVBoxLayout(self)
        self.current_character = QLabel("当前角色", self)
        self.current_character.setObjectName("currentPlayerCharacter")
        layout.addWidget(self.current_character)
        body = QHBoxLayout()
        self.characters = QListWidget(self)
        self.characters.setObjectName("characterRoster")
        self.details = QTextBrowser(self)
        self.details.setObjectName("characterPublicDetails")
        self.details.setOpenExternalLinks(False)
        body.addWidget(self.characters, 1)
        body.addWidget(self.details, 2)
        layout.addLayout(body)
        self.edit_identity_button = QPushButton("编辑身份", self)
        self.edit_identity_button.setObjectName("editCharacterIdentity")
        self.edit_identity_button.clicked.connect(self._edit_selected_identity)
        layout.addWidget(self.edit_identity_button)
        close_button = QPushButton("关闭", self)
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)
        self.characters.currentRowChanged.connect(self._show_selected)
        self.refresh()

    def refresh(self):
        self.characters.clear()
        self._entries = []
        self.edit_identity_button.setEnabled(False)
        session = self.session
        if session is None:
            self.current_character.setText("当前角色：未进入世界")
            return
        player_id = getattr(session, "player_character_id", session.player_id)
        player = next((item for item in session.agent_contexts if item.character_id == player_id), None)
        identities = getattr(session, "identity_manager", None)
        player_name = (identities.display_name_for(player_id, "玩家角色") if identities is not None
                       else player.character_state.name if player is not None else "玩家角色")
        self.current_character.setText(f"当前角色：{player_name}")
        for context in session.agent_contexts:
            authority = session.authority_manager.authority_for(context.character_id)
            if authority is None:
                continue
            is_player = authority.authority_level is AuthorityLevel.PLAYER
            category = "当前角色" if is_player else (
                "重要人物" if authority.authority_level is AuthorityLevel.IMPORTANT_CHARACTER else "背景人物"
            )
            presence = session.presence_manager.get(context.character_id)
            status = _public_presence(presence)
            relationships = ()
            if not is_player and hasattr(session.executor.relationship_manager, "for_character"):
                relationships = tuple(
                    relation for relation in session.executor.relationship_manager.for_character(player_id)
                    if relation.target_id == context.character_id
                )
            self._entries.append((context, category, status, relationships, authority))
            label = identities.display_name_for(context.character_id, "角色") if identities is not None else context.character_state.name
            self.characters.addItem(f"{label} · {category}")
        if self._entries:
            self.characters.setCurrentRow(0)

    def _show_selected(self, index):
        if index < 0 or index >= len(self._entries):
            self.details.clear()
            return
        context, category, status, relationships, authority = self._entries[index]
        identities = getattr(self.session, "identity_manager", None)
        identity = identities.get(context.character_id) if identities is not None else None
        shown_name = identity.display_name if identity is not None else context.character_state.name
        self.edit_identity_button.setEnabled(bool(identity and identity.editable))
        can_view = self.session.authority_manager.check_visibility_permission(
            self.session.player_character_id, context.character_id, "public_status"
        )
        lines = [shown_name, category]
        if identity is not None:
            lines.append(f"身份来源：{identity.naming_source}")
            if identity.aliases:
                lines.append("别名：" + "、".join(identity.aliases))
            if identity.public_description:
                lines.append(identity.public_description)
        if can_view:
            role = context.character_state.role
            if role:
                lines.append(f"身份：{role}")
            lines.append(f"公开状态：{status}")
        if relationships:
            relation = relationships[0]
            values = ", ".join(
                f"{label} {getattr(relation, field)}"
                for field, label in (("trust", "信任"), ("respect", "尊重"), ("fear", "畏惧"),
                                     ("affinity", "亲近"), ("hostility", "敌意"))
                if hasattr(relation, field)
            )
            if values:
                lines.append("与你的关系：" + values)
        lifecycle = getattr(self.session, "relationship_lifecycle_manager", None)
        if can_view and lifecycle is not None:
            from cognitive_sandbox.relationship.lifecycle import RelationshipStage
            stage = lifecycle.stage_for(self.session.player_character_id, context.character_id)
            if stage is not RelationshipStage.UNKNOWN:
                stage_labels = {
                    RelationshipStage.STRANGER: "陌生",
                    RelationshipStage.ACQUAINTANCE: "初识",
                    RelationshipStage.FAMILIAR: "熟悉",
                    RelationshipStage.COOPERATIVE: "合作",
                    RelationshipStage.TRUSTED: "信任",
                    RelationshipStage.CLOSE: "亲近",
                    RelationshipStage.CONFLICTED: "冲突",
                    RelationshipStage.BROKEN: "破裂",
                }
                familiarity = lifecycle.dynamics_for(
                    self.session.player_character_id, context.character_id
                ).familiarity
                familiarity_label = "熟悉" if familiarity >= .35 else "初识" if familiarity > 0 else "陌生"
                lines.append(f"认识程度：{familiarity_label} · 关系：{stage_labels.get(stage, '未知')}")
        lines.append("可控制：是" if authority.controllable else "可控制：否")
        self.details.setPlainText("\n".join(lines))

    def _edit_selected_identity(self):
        index = self.characters.currentRow()
        if index < 0 or index >= len(self._entries):
            return None
        session = self.session
        identities = getattr(session, "identity_manager", None)
        if identities is None:
            return None
        context = self._entries[index][0]
        from cognitive_sandbox.presentation.character.identity_editor_dialog import IdentityEditorDialog
        dialog = IdentityEditorDialog(identities, context.character_id, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()
            self.characters.setCurrentRow(index)
        return dialog


def _public_presence(presence):
    if presence is None:
        return "状态未知"
    value = getattr(presence, "availability", None)
    value = getattr(value, "value", value)
    return {
        "ACTIVE": "在场",
        "AVAILABLE": "可联系",
        "INTRODUCED": "已认识",
        "LEFT": "已离开",
        "UNKNOWN": "尚未出现",
    }.get(value, "状态未知")

