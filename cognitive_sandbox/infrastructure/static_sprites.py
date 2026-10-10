from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap


class StaticSpriteRenderer:
    """Loads a portrait image, leaving the render seam open for a future Live2D adapter."""

    def __init__(self, asset_dir: Path) -> None:
        self.asset_dir = asset_dir

    def render(self, sprite_key: str, expression: str = "neutral") -> QPixmap:
        for path in (self.asset_dir / f"{sprite_key}_{expression}.png", self.asset_dir / f"{sprite_key}.png"):
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                return pixmap
        return self._placeholder(sprite_key)

    @staticmethod
    def _placeholder(label: str) -> QPixmap:
        pixmap = QPixmap(480, 640)
        pixmap.fill(Qt.GlobalColor.transparent)
        from PySide6.QtGui import QColor, QPainter, QPen

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor("#d5b3a1"))
        painter.setPen(QPen(QColor("#d5b3a1"), 2))
        painter.drawEllipse(110, 35, 260, 300)
        painter.setBrush(QColor("#e9d4c1"))
        painter.drawRoundedRect(55, 285, 370, 355, 150, 95)
        painter.setPen(QColor("#fff8ee"))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom, f"{label} · 立绘占位")
        painter.end()
        return pixmap
