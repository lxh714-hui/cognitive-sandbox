from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterable, Mapping

from cognitive_sandbox.domain.action_intent import ActionIntent
from cognitive_sandbox.domain.actions import ActionCandidate


@dataclass(frozen=True)
class ActionSemanticFingerprint:
    objective: str
    method: str
    risk: float
    relationship_effect: str
    expected_effect: str
    target_opportunity: str | None = None


@dataclass(frozen=True)
class ActionSemanticMapping:
    candidate: ActionCandidate
    matched_candidate: ActionCandidate | None
    fingerprint: ActionSemanticFingerprint
    target_opportunity: str | None = None
    classification: str = "new_branch"

    @property
    def reused_existing_branch(self) -> bool:
        return self.matched_candidate is not None

    @property
    def expands_opportunity(self) -> bool:
        return self.target_opportunity is not None and self.matched_candidate is None


class ActionSemanticMapper:
    """Match equivalent action proposals without collapsing meaningful choices.

    A caller can pass the candidate actions attached to the active World Tree
    node. Exact objective/method/effect matching reuses that candidate; changes
    in approach, risk, expected result, or social impact remain separate choices.
    """

    _DEFAULT_RISK = {
        "observe": .15, "look": .15, "ask": .2, "talk": .2, "inspect": .25,
        "move": .3, "explore": .35, "help": .3, "protect": .45,
        "rest": .05, "wait": .05,
    }
    _DEFAULT_EFFECT = {
        "observe": "gain_visible_information", "look": "gain_visible_information",
        "ask": "gain_information", "talk": "exchange_information",
        "inspect": "inspect_target", "move": "change_location",
        "explore": "explore_area", "help": "assist_target",
        "protect": "protect_target", "rest": "recover_time",
        "wait": "advance_time",
    }

    def fingerprint(self, action: ActionIntent | ActionCandidate) -> ActionSemanticFingerprint:
        if isinstance(action, ActionIntent):
            intent = action.intent.casefold()
            params = action.parameters
            target = action.target or action.object or ""
            raw_input = action.raw_input
        elif isinstance(action, ActionCandidate):
            intent = str(action.intent).casefold()
            params = action.metadata
            target = action.target or action.target_refs[0] if action.target_refs else (action.target or "")
            raw_input = str(params.get("raw_input", ""))
        else:
            raise TypeError("action must be an ActionIntent or ActionCandidate.")

        objective = _text(params.get("objective")) or f"{intent}:{target.casefold()}"
        stealth = any(token in raw_input for token in ("偷偷", "悄悄", "暗中", "不被发现"))
        method = _text(params.get("method")) or ("stealth" if stealth else _method(intent))
        raw_risk = params.get("risk", self._DEFAULT_RISK.get(intent, .3))
        if isinstance(raw_risk, bool) or not isinstance(raw_risk, (int, float)) or not 0 <= raw_risk <= 1:
            raise ValueError("action risk must be between 0 and 1.")
        relationship = _text(params.get("relationship_effect")) or _relationship_effect(intent)
        effect = _text(params.get("expected_effect")) or self._DEFAULT_EFFECT.get(intent, intent)
        target_opportunity = params.get("target_opportunity")
        if target_opportunity is not None and (not isinstance(target_opportunity, str) or not target_opportunity.strip()):
            target_opportunity = None
        return ActionSemanticFingerprint(objective, method, float(raw_risk), relationship, effect,
                                         target_opportunity)

    def candidate_for(self, action: ActionIntent) -> ActionCandidate:
        if not isinstance(action, ActionIntent):
            raise TypeError("action must be an ActionIntent.")
        fingerprint = self.fingerprint(action)
        metadata = {
            **dict(action.parameters),
            "raw_input": action.raw_input,
            "objective": fingerprint.objective,
            "method": fingerprint.method,
            "risk": fingerprint.risk,
            "relationship_effect": fingerprint.relationship_effect,
            "expected_effect": fingerprint.expected_effect,
        }
        return ActionCandidate(
            action_type=action.intent,
            actor_id=action.actor_id,
            intent=action.intent,
            target=action.target or action.object,
            target_refs=(action.target or action.object,) if action.target or action.object else (),
            motivation="player_intent",
            metadata=metadata,
        )

    def map_to_existing(
        self,
        action: ActionIntent,
        existing: Iterable[ActionCandidate] = (),
        opportunities: Iterable = (),
    ) -> ActionSemanticMapping:
        candidate = self.candidate_for(action)
        proposed = self.fingerprint(candidate)
        candidates = tuple(existing)
        if any(not isinstance(item, ActionCandidate) for item in candidates):
            raise TypeError("existing must contain ActionCandidate values.")
        opportunities = tuple(opportunities)
        opportunity_match = None
        opportunity_candidate = None
        for opportunity in opportunities:
            for option in self._opportunity_candidates(opportunity, action.actor_id):
                if self._equivalent(proposed, self.fingerprint(option)):
                    opportunity_match = getattr(opportunity, "opportunity_id", None)
                    opportunity_candidate = option
                    break
            if opportunity_match:
                break
        match = next((item for item in candidates if self._equivalent(proposed, self.fingerprint(item))), None)
        if match is None and opportunity_candidate is not None:
            match = opportunity_candidate
        target_opportunity = (action.parameters.get("target_opportunity")
                              or opportunity_match
                              or (match.metadata.get("opportunity_id") if match is not None else None))
        if target_opportunity:
            proposed = ActionSemanticFingerprint(
                proposed.objective, proposed.method, proposed.risk,
                proposed.relationship_effect, proposed.expected_effect,
                str(target_opportunity),
            )
        classification = "reuse_existing" if match is not None else (
            "expand_branch" if target_opportunity else "new_branch"
        )
        return ActionSemanticMapping(candidate, match, proposed, target_opportunity, classification)

    @staticmethod
    def _opportunity_candidates(opportunity, actor_id):
        explicit = tuple(getattr(opportunity, "candidate_actions", ()))
        if explicit:
            return explicit
        result = []
        for label in tuple(getattr(opportunity, "possible_actions", ())):
            text = label.casefold()
            if any(word in text for word in ("忽略", "离开", "搁置", "暂时不")):
                continue
            intent = next((key for tokens, key in (
                (("问", "询问", "打听"), "ask"), (("看", "查看", "检查"), "inspect"),
                (("去", "前往"), "move"), (("帮助", "协助"), "help"),
                (("观察", "留意"), "observe"),
            ) if any(token in text for token in tokens)), "explore")
            result.append(ActionCandidate(
                action_type=intent, intent=intent, actor_id=actor_id,
                motivation="opportunity_candidate",
                metadata={"objective": f"{intent}:{getattr(opportunity, 'opportunity_id', '')}",
                          "method": intent, "expected_effect": intent,
                          "opportunity_id": getattr(opportunity, "opportunity_id", None)},
            ))
        return tuple(result)

    @staticmethod
    def _equivalent(left: ActionSemanticFingerprint, right: ActionSemanticFingerprint) -> bool:
        return (
            left.objective == right.objective
            and left.method == right.method
            and abs(left.risk - right.risk) <= .1
            and left.relationship_effect == right.relationship_effect
            and left.expected_effect == right.expected_effect
        )


def _text(value):
    return value.strip().casefold() if isinstance(value, str) else ""


def _method(intent):
    return {"look": "observe", "ask": "conversation", "talk": "conversation"}.get(intent, intent)


def _relationship_effect(intent):
    return {
        "talk": "social_contact", "ask": "social_contact", "help": "positive_support",
        "protect": "protective_support", "observe": "no_direct_change",
        "look": "no_direct_change", "inspect": "no_direct_change",
    }.get(intent, "unspecified")
