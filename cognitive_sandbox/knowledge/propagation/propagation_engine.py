from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime, timezone

from cognitive_sandbox.knowledge.models.knowledge_record import KnowledgeRecord, KnowledgeType
from cognitive_sandbox.knowledge.models.knowledge_source import KnowledgeSource
from cognitive_sandbox.knowledge.models.knowledge_visibility import KnowledgeVisibility
from cognitive_sandbox.knowledge.models.world_fact import WorldFact
from cognitive_sandbox.knowledge.propagation.propagation_rule import PropagationRule


_DEFAULT_RULES = (
    PropagationRule("participants", KnowledgeType.DIRECT, 1.0, "direct_experience", "亲身经历", "你亲身经历了：{fact_content}"),
    PropagationRule("observers", KnowledgeType.OBSERVED, 0.8, "observation", "现场观察", "你观察到与此事有关的迹象。"),
    PropagationRule("reported_to", KnowledgeType.REPORTED, 0.7, "report", "他人转述", "有人向你转述了相关情况。"),
    PropagationRule("rumor_recipients", KnowledgeType.RUMOR, 0.35, "rumor", "未经证实的传闻", "你听到一则有关此事的传闻。"),
    PropagationRule("inferred_by", KnowledgeType.INFERRED, 0.55, "inference", "个人推断", "你根据已有线索推测此事可能发生过。"),
)


class PropagationEngine:
    """Create scoped knowledge only for recipients explicitly named by a rule input."""

    def __init__(self, rules: Iterable[PropagationRule] | None = None, *, clock=None):
        self._rules = tuple(rules) if rules is not None else _DEFAULT_RULES
        if any(not isinstance(rule, PropagationRule) for rule in self._rules):
            raise TypeError("rules must contain PropagationRule values.")
        self._clock = clock or (lambda: datetime.now(timezone.utc).isoformat())

    def propagate(
        self,
        fact: WorldFact,
        *,
        participants: Iterable[str] = (),
        observers: Iterable[str] = (),
        reported_to: Iterable[str] = (),
        rumor_recipients: Iterable[str] = (),
        inferred_by: Iterable[str] = (),
        summaries: Mapping[str, str] | None = None,
    ) -> tuple[KnowledgeRecord, ...]:
        if not isinstance(fact, WorldFact):
            raise TypeError("fact must be a WorldFact.")
        audiences = {
            "participants": _ids(participants),
            "observers": _ids(observers),
            "reported_to": _ids(reported_to),
            "rumor_recipients": _ids(rumor_recipients),
            "inferred_by": _ids(inferred_by),
        }
        summaries = summaries or {}
        records: list[KnowledgeRecord] = []
        seen: set[tuple[str, str]] = set()
        for rule in self._rules:
            for owner_id in audiences[rule.audience]:
                key = (owner_id, rule.audience)
                if key in seen:
                    continue
                seen.add(key)
                # Non-direct knowledge gets only an explicitly authored summary,
                # or a cautious rule template that contains no world-fact text.
                if rule.knowledge_type is KnowledgeType.DIRECT:
                    known_content = rule.known_content_template.format(fact_content=fact.content)
                else:
                    known_content = summaries.get(owner_id, rule.known_content_template)
                source = KnowledgeSource(
                    source_id=f"{fact.id}:{rule.source_type}:{owner_id}",
                    source_type=rule.source_type,
                    description=rule.source_description,
                    actor_id=fact.related_entities[0] if fact.related_entities else None,
                )
                records.append(KnowledgeRecord(
                    owner_id=owner_id,
                    fact_id=fact.id,
                    knowledge_type=rule.knowledge_type,
                    source=source,
                    confidence=rule.confidence,
                    created_at=self._clock(),
                    known_content=known_content,
                    visibility=KnowledgeVisibility(),
                ))
        return tuple(records)


def _ids(values: Iterable[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise TypeError("audience must be a collection of character IDs.")
    result = tuple(values)
    if any(not isinstance(value, str) or not value.strip() for value in result):
        raise ValueError("audience IDs must be non-empty strings.")
    return result
