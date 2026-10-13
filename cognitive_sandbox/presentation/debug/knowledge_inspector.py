from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import QComboBox, QLineEdit, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from cognitive_sandbox.knowledge.retrieval.knowledge_query import KnowledgeQuery


@dataclass(frozen=True)
class KnowledgeEntry:
    character_id: str
    fact_id: str
    content: str
    knowledge_type: str
    confidence: float
    source_type: str
    created_at: str


class KnowledgeInspector(QWidget):
    """Inspect only information returned by the selected character's retriever."""

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.character_selector = QComboBox(self)
        self.character_selector.setObjectName("knowledgeCharacterSelector")
        self.query_input = QLineEdit(self)
        self.query_input.setObjectName("knowledgeQueryInput")
        self.query_input.setPlaceholderText("按内容筛选该角色已知信息")
        self.tree = QTreeWidget(self)
        self.tree.setObjectName("knowledgeInspectorTree")
        self.tree.setHeaderLabels(("所选角色可检索的信息", "来源与可信度"))
        self.tree.setEditTriggers(QTreeWidget.EditTrigger.NoEditTriggers)
        layout = QVBoxLayout(self)
        layout.addWidget(self.character_selector)
        layout.addWidget(self.query_input)
        layout.addWidget(self.tree)
        minds = getattr(session.executor, "character_minds", {})
        for context in tuple(getattr(session, "agent_contexts", ())):
            mind = minds.get(context.character_id)
            name = getattr(getattr(mind, "identity", None), "name", None) or context.character_state.name
            self.character_selector.addItem(name, context.character_id)
        self.character_selector.currentIndexChanged.connect(self.refresh)
        self.query_input.textChanged.connect(self.refresh)
        self.refresh()

    def snapshot(self, character_id: str, query: str = "", *, limit: int = 50):
        retriever = getattr(self.session, "knowledge_retriever", None)
        if retriever is None:
            retriever = getattr(self.session.executor, "knowledge_retriever", None)
        if retriever is None:
            return ()
        records = retriever.retrieve(character_id, KnowledgeQuery(text=query, limit=limit))
        store = getattr(retriever, "backing_store", None)
        entries = []
        for record in records:
            # The retriever scopes the query; this final check guards the view
            # against a faulty adapter returning a record outside that scope.
            if not record.visibility.allows(character_id, record.owner_id):
                continue
            fact = store.get_fact(record.fact_id) if store is not None else None
            content = record.known_content or getattr(fact, "content", "")
            if not content:
                continue
            source_type = getattr(record.source.source_type, "value", record.source.source_type)
            entries.append(KnowledgeEntry(
                character_id, record.fact_id, content, record.knowledge_type.value,
                record.confidence, str(source_type), record.created_at,
            ))
        return tuple(entries)

    def refresh(self, *_args):
        self.tree.clear()
        character_id = self.character_selector.currentData()
        if not isinstance(character_id, str) or not character_id:
            return ()
        entries = self.snapshot(character_id, self.query_input.text())
        for entry in entries:
            item = QTreeWidgetItem((entry.content, f"{entry.knowledge_type} · 可信度 {entry.confidence:.2f}"))
            item.setToolTip(0, f"source={entry.source_type}; created={entry.created_at}; fact={entry.fact_id}")
            self.tree.addTopLevelItem(item)
        return entries
