from __future__ import annotations


class DirectorViewModel:
    """Project a DirectorResult into player-safe display strings."""

    def present(self, result):
        return {
            "status": result.constraint.status.value,
            "explanation": result.explanation,
            "intent": result.intent.description,
            "threads": result.affected_threads,
            "paths": tuple({
                "title": path.title,
                "steps": path.steps,
                "score": path.score,
                "rationale": path.rationale,
            } for path in result.paths),
        }
