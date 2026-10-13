import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from cognitive_sandbox.presentation.director.director_panel import DirectorPanel


def test_director_panel_exposes_constraint_add_edit_remove_controls():
    app = QApplication.instance() or QApplication([])
    panel = DirectorPanel()
    assert panel.constraint_editor.objectName() == "directorConstraintEditor"
    assert panel.constraint_editor.add_button.text() == "新增"
    assert panel.constraint_editor.edit_button.text() == "修改所选"
    assert panel.constraint_editor.remove_button.text() == "删除所选"
    panel.close()
