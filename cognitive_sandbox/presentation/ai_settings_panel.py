from __future__ import annotations

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QComboBox, QFormLayout, QLineEdit, QWidget

from cognitive_sandbox.domain.llm_config import LLMConfig


class AISettingsPanel(QWidget):
    """Editable, in-memory provider settings; credentials are supplied separately."""

    PROVIDERS = ("openai-compatible", "local-compatible")

    SETTINGS_PREFIX = "ai"

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        settings: QSettings | None = None,
    ) -> None:
        super().__init__(parent)
        self._settings = settings if settings is not None else QSettings("CognitiveSandbox", "CognitiveSandbox")
        form = QFormLayout(self)

        self.provider = QComboBox(self)
        self.provider.setObjectName("provider")
        self.provider.setEditable(True)
        self.provider.addItems(self.PROVIDERS)
        self.provider.setCurrentText(self.PROVIDERS[0])

        self.model_name = QLineEdit("gpt-4o-mini", self)
        self.model_name.setObjectName("modelName")
        self.base_url = QLineEdit("https://api.openai.com/v1", self)
        self.base_url.setObjectName("baseUrl")

        form.addRow("Provider", self.provider)
        form.addRow("Model", self.model_name)
        form.addRow("Base URL", self.base_url)
        self.load_settings()

    def load_settings(self) -> None:
        """Load provider details from QSettings; credentials are never read."""
        self.provider.setCurrentText(
            str(self._settings.value(f"{self.SETTINGS_PREFIX}/provider", self.PROVIDERS[0]))
        )
        self.model_name.setText(
            str(self._settings.value(f"{self.SETTINGS_PREFIX}/model_name", "gpt-4o-mini"))
        )
        self.base_url.setText(
            str(self._settings.value(f"{self.SETTINGS_PREFIX}/base_url", "https://api.openai.com/v1"))
        )

    def save_settings(self) -> None:
        """Persist non-secret provider settings only."""
        self._settings.setValue(f"{self.SETTINGS_PREFIX}/provider", self.provider.currentText().strip())
        self._settings.setValue(f"{self.SETTINGS_PREFIX}/model_name", self.model_name.text().strip())
        self._settings.setValue(f"{self.SETTINGS_PREFIX}/base_url", self.base_url.text().strip())
        self._settings.sync()

    def to_config(self, *, api_key: str = "") -> LLMConfig:
        """Return an LLMConfig without persisting or retaining the API key."""
        return LLMConfig(
            api_key=api_key,
            base_url=self.base_url.text().strip(),
            model_name=self.model_name.text().strip(),
        )

    def load_config(self, config: LLMConfig) -> None:
        if not isinstance(config, LLMConfig):
            raise TypeError("config must be an LLMConfig")
        self.model_name.setText(config.model_name)
        self.base_url.setText(config.base_url)
