from __future__ import annotations

import logging
from collections.abc import Callable

from PySide6.QtCore import QObject, Signal, Slot


logger = logging.getLogger(__name__)


class RoleplayWorker(QObject):
    """Run one prepared roleplay turn away from the Qt UI thread."""

    succeeded = Signal(object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, operation: Callable[[], object]) -> None:
        super().__init__()
        if not callable(operation):
            raise TypeError("operation must be callable")
        self._operation = operation

    @Slot()
    def run(self) -> None:
        try:
            self.succeeded.emit(self._operation())
        except Exception as error:
            logger.exception("Roleplay action execution failed")
            self.failed.emit(str(error) or error.__class__.__name__)
        finally:
            self.finished.emit()
