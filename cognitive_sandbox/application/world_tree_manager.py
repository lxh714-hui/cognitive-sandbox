from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from uuid import uuid4

from cognitive_sandbox.application.branch_generator import BranchGenerator
from cognitive_sandbox.application.lazy_expander import LazyExpander
from cognitive_sandbox.domain.actions import ActionCandidate
from cognitive_sandbox.domain.story import ExpansionPolicy, StoryBranch


class WorldTreeManager:
    """Persisted, lazily expanded action branches; selection alone is not an event."""

    def __init__(self, world_id: str, snapshot=None, *, expander=None, world_memory=None):
        if not isinstance(world_id, str) or not world_id.strip():
            raise ValueError("world_id must not be empty.")
        self.world_id = world_id
        self.expander = expander or LazyExpander(BranchGenerator())
        self.world_memory = world_memory
        self.root = StoryBranch("main", None, world_id, 0, None)
        self.branches = {self.root.branch_id: self.root}
        self.current_branch_id = self.root.branch_id
        self.opportunity_branches: dict[str, tuple[str, ...]] = {}
        self.deleted_branch_ids: set[str] = set()
        if snapshot:
            self.restore(snapshot)

    @property
    def candidate_actions(self) -> tuple[ActionCandidate, ...]:
        return tuple(
            branch.divergence_action for key, branch in self.branches.items()
            if key != self.root.branch_id and key not in self.deleted_branch_ids
            and branch.divergence_action is not None
        )

    def register_opportunity(self, opportunity) -> tuple[StoryBranch, ...]:
        opportunity_id = getattr(opportunity, "opportunity_id", None)
        if not isinstance(opportunity_id, str) or not opportunity_id:
            raise TypeError("opportunity must have an opportunity_id.")
        existing_ids = self.opportunity_branches.get(opportunity_id)
        if existing_ids is not None:
            return tuple(self.branches[item] for item in existing_ids if item in self.branches)
        actions = tuple(getattr(opportunity, "candidate_actions", ()))
        if not actions:
            from cognitive_sandbox.application.action_semantic_mapper import ActionSemanticMapper
            actions = tuple(
                item for item in ActionSemanticMapper._opportunity_candidates(opportunity, "world")
                if "opportunity_id" in item.metadata
                and not any(word in str(item.metadata.get("objective", ""))
                            for word in ("ignore", "离开", "搁置"))
            )
        if any(not isinstance(item, ActionCandidate) for item in actions):
            raise TypeError("opportunity candidate_actions must contain ActionCandidate values.")
        tagged = tuple(_tag_action(item, opportunity_id) for item in actions)
        branch = self.branches.get(self.current_branch_id, self.root)
        children = self.expander.expand(branch, tagged, ExpansionPolicy(3, 500))
        self.branches.update((item.branch_id, item) for item in children)
        self.opportunity_branches[opportunity_id] = tuple(item.branch_id for item in children)
        if self.world_memory is not None:
            for item in children:
                self.world_memory.record_world_tree(
                    "branch_expanded", item.branch_id,
                    cause=f"opportunity:{opportunity_id}",
                    metadata={"parent_branch_id": item.parent_branch_id,
                              "opportunity_id": opportunity_id},
                )
        return children

    def record_action(self, action: ActionCandidate, *, matched_candidate=None, opportunity_id=None):
        if not isinstance(action, ActionCandidate):
            raise TypeError("action must be an ActionCandidate.")
        matched_branch = next((branch for branch in self.branches.values()
                               if matched_candidate is not None and
                               (branch.divergence_action is matched_candidate
                                or branch.divergence_action == matched_candidate)), None)
        if matched_branch is None:
            source = self.branches.get(self.current_branch_id, self.root)
            children = self.expander.expand(source, (action,), ExpansionPolicy(1, 500))
            if not children:
                return None
            matched_branch = children[0]
            self.branches[matched_branch.branch_id] = matched_branch
            if self.world_memory is not None:
                self.world_memory.record_world_tree(
                    "branch_expanded", matched_branch.branch_id,
                    cause="action created a lazy branch",
                    metadata={"parent_branch_id": matched_branch.parent_branch_id,
                              "action_type": action.action_type},
                )
        self.current_branch_id = matched_branch.branch_id
        if self.world_memory is not None:
            self.world_memory.record_world_tree(
                "branch_selected", matched_branch.branch_id,
                cause="player or NPC action selected this branch",
                metadata={"action_type": action.action_type, "opportunity_id": opportunity_id},
            )
        if opportunity_id:
            current = self.opportunity_branches.get(opportunity_id, ())
            if matched_branch.branch_id not in current:
                self.opportunity_branches[opportunity_id] = (*current, matched_branch.branch_id)
        return matched_branch

    def delete_branch(self, branch_id: str) -> bool:
        if branch_id == self.root.branch_id or branch_id not in self.branches:
            return False
        descendants = {branch_id}
        changed = True
        while changed:
            changed = False
            for key, branch in self.branches.items():
                if branch.parent_branch_id in descendants and key not in descendants:
                    descendants.add(key)
                    changed = True
        self.deleted_branch_ids.update(descendants)
        if self.world_memory is not None:
            for deleted_id in sorted(descendants):
                self.world_memory.record_world_tree(
                    "branch_closed", deleted_id, cause="branch removed from active world tree",
                )
        if self.current_branch_id in descendants:
            self.current_branch_id = self.root.branch_id
        return True

    def record_merge(self, source_branch_ids, merged_branch_id, *, reason=""):
        """Record a merge performed by a higher-level tree operation."""
        sources = tuple(source_branch_ids)
        if not isinstance(merged_branch_id, str) or not merged_branch_id.strip():
            raise ValueError("merged_branch_id must not be empty.")
        if self.world_memory is not None:
            self.world_memory.record_world_tree(
                "branches_merged", merged_branch_id, cause=reason or "branches converged",
                metadata={"source_branch_ids": sources},
            )

    def snapshot(self) -> dict:
        return {
            "world_id": self.world_id,
            "root": self.root,
            "branches": tuple(self.branches.values()),
            "current_branch_id": self.current_branch_id,
            "opportunity_branches": {key: tuple(value) for key, value in self.opportunity_branches.items()},
            "deleted_branch_ids": tuple(sorted(self.deleted_branch_ids)),
            "expansion_count": self.expander.total_expansions,
        }

    def restore(self, snapshot: Mapping) -> None:
        if not isinstance(snapshot, Mapping):
            raise TypeError("world tree snapshot must be a mapping.")
        root = snapshot.get("root", self.root)
        branches = tuple(snapshot.get("branches", (root,)))
        if not isinstance(root, StoryBranch) or any(not isinstance(item, StoryBranch) for item in branches):
            raise TypeError("world tree snapshot contains invalid branches.")
        # Older save paths may identify the same instance using its public
        # WorldDocument ID while the runtime used a generated ID. Keep the
        # persisted branch topology and rebind it to the restored session ID.
        if root.world_id != self.world_id or any(item.world_id != self.world_id for item in branches):
            root = replace(root, world_id=self.world_id)
            branches = tuple(replace(item, world_id=self.world_id) for item in branches)
        self.root = root
        self.branches = {item.branch_id: item for item in branches}
        self.branches.setdefault(root.branch_id, root)
        current = snapshot.get("current_branch_id", root.branch_id)
        self.current_branch_id = current if current in self.branches else root.branch_id
        self.opportunity_branches = {
            str(key): tuple(item for item in value if item in self.branches)
            for key, value in snapshot.get("opportunity_branches", {}).items()
        }
        self.deleted_branch_ids = set(snapshot.get("deleted_branch_ids", ()))
        # Expansion history is persisted as metadata; the existing lazy expander
        # retains its safety cap and is not eagerly populated on restore.


def _tag_action(action: ActionCandidate, opportunity_id: str) -> ActionCandidate:
    return ActionCandidate(
        action_type=action.action_type, actor_id=action.actor_id, intent=action.intent,
        target=action.target, target_refs=action.target_refs, motivation=action.motivation,
        metadata={**dict(action.metadata), "opportunity_id": opportunity_id},
        action_id=action.action_id or f"candidate_{uuid4().hex}",
    )
