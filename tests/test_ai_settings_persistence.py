from __future__ import annotations

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from cognitive_sandbox.presentation.ai_settings_panel import AISettingsPanel


def test_ai_settings_round_trip_without_persisting_api_key(tmp_path):
    app = QApplication.instance() or QApplication([])
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)

    panel = AISettingsPanel(settings=settings)
    panel.provider.setCurrentText("ollama-compatible")
    panel.model_name.setText("qwen2.5")
    panel.base_url.setText("http://localhost:11434/v1")
    config = panel.to_config(api_key="must-not-be-saved")
    panel.save_settings()

    reopened = AISettingsPanel(settings=settings)
    assert reopened.provider.currentText() == "ollama-compatible"
    assert reopened.model_name.text() == "qwen2.5"
    assert reopened.base_url.text() == "http://localhost:11434/v1"
    assert config.api_key == "must-not-be-saved"
    assert not any("key" in key.casefold() for key in settings.allKeys())

    panel.close()
    reopened.close()
    app.processEvents()
