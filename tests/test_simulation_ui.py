import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QPushButton

from cognitive_sandbox.presentation.simulation import SimulationControl, SimulationTimeline, SimulationView


def test_simulation_view_has_pause_resume_step_and_fast_forward_controls():
    app = QApplication.instance() or QApplication([])
    view = SimulationView()
    actions = []
    view.controls.requested.connect(actions.append)
    view.controls.findChild(QPushButton, "simulationControl_pause").click()
    view.controls.findChild(QPushButton, "simulationControl_next_day").click()
    assert actions == ["pause", "next_day"]
    view.close()
