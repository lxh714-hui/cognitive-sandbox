from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from PySide6.QtWidgets import QVBoxLayout, QTextBrowser, QWidget


@dataclass(frozen=True)
class ReplayRow:
    timestamp: str
    event_type: str
    actor_ids: tuple[str, ...]
    emotion_changes: tuple[str, ...] = ()
    relationship_changes: tuple[str, ...] = ()
    narrative_changes: tuple[str, ...] = ()
    director_constraints: tuple[str, ...] = ()


class SimulationReplayInspector(QWidget):
    """Read-only chronological view over a completed simulation report."""

    def __init__(self, report, parent=None):
        super().__init__(parent)
        self.report = report
        self.view = QTextBrowser(self)
        self.view.setObjectName("simulationReplayView")
        self.view.setOpenExternalLinks(False)
        self.view.setReadOnly(True)
        layout = QVBoxLayout(self)
        layout.addWidget(self.view)
        self.refresh()

    def rows(self):
        emotions_by_event = {}
        for summary in self.report.characters.values():
            for change in summary.emotion_changes:
                emotions_by_event.setdefault(change.source_event_id, []).append(
                    f"{summary.character_id}: {change.emotion_type} {change.delta:+.2f} ({change.reason})"
                )
        relationships_by_event = {}
        for change in self.report.state_changes:
            if getattr(change, "target_type", None) == "relationship":
                relationships_by_event.setdefault(getattr(change, "event_id", ""), []).append(
                    f"{change.target_id}.{change.field}: {change.old_value}→{change.new_value}"
                )
        narrative_changes = tuple(
            f"{change.title}: {change.before_status}→{change.after_status}, "
            f"进度 {change.before_progress:.0%}→{change.after_progress:.0%}; "
            f"冲突 {change.before_conflict or '无变化'}→{change.after_conflict or '无变化'}"
            for change in self.report.thread_changes
        )
        rows = []
        start = datetime.fromisoformat(self.report.start_time)
        for event in sorted(self.report.events, key=lambda item: item.timestamp):
            try:
                day = max(1, (datetime.fromisoformat(event.timestamp) - start).days + 1)
            except (TypeError, ValueError):
                day = 1
            rows.append(ReplayRow(
                f"Day {day} · {event.timestamp}", event.event_type, event.actor_ids,
                tuple(emotions_by_event.get(event.event_id, ())),
                tuple(relationships_by_event.get(event.event_id, ())), (),
            ))
        relationship_summary = tuple(
            f"{change.source_id}→{change.target_id}: "
            f"trust={change.trust:.1f}, respect={change.respect:.1f}, "
            f"fear={change.fear:.1f}, hostility={change.hostility:.1f}"
            for summary in self.report.characters.values()
            for change in summary.relationship_changes
        )
        if relationship_summary or narrative_changes:
            rows.append(ReplayRow(
                f"模拟结束 · {self.report.end_time}", "simulation_summary", (), (),
                relationship_summary, narrative_changes,
            ))
        for constraint in self.report.director_constraints:
            status = getattr(getattr(constraint, "status", None), "value", "PENDING")
            intent = getattr(constraint, "intent", None)
            rows.append(ReplayRow(
                f"导演约束 · {self.report.end_time}", status, (), (), (),
                (),
                (f"{status} · {getattr(constraint, 'target', None) or '世界'}: "
                 f"{getattr(intent, 'description', '')}",),
            ))
        return tuple(rows)

    def refresh(self):
        lines = []
        for row in self.rows():
            lines.append(f"{row.timestamp}\n事件：{row.event_type} · {', '.join(row.actor_ids) or '世界'}")
            lines.extend(f"情绪变化：{item}" for item in row.emotion_changes)
            lines.extend(f"关系变化：{item}" for item in row.relationship_changes)
            lines.extend(f"剧情变化：{item}" for item in row.narrative_changes)
            lines.extend(f"导演约束：{item}" for item in row.director_constraints)
            lines.append("")
        self.view.setPlainText("\n".join(lines) if lines else "暂无模拟记录。")
        return tuple(lines)
