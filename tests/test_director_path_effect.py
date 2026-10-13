from cognitive_sandbox.director.constraint_type import ConstraintType
from cognitive_sandbox.director.director_intent import DirectorIntent, DirectorIntentType
from cognitive_sandbox.director.director_constraint import DirectorConstraint
from cognitive_sandbox.director.director_path_finder import DirectorPath, DirectorPathFinder


def test_path_finder_applies_constraint_score_and_forbid_to_candidate_routes():
    class Evaluator:
        def score_path(self, text, constraints=(), *, candidate_id="path"):
            if "romance" in text:
                return True, -.2, ()
            return True, .1, ()

    intent = DirectorIntent(DirectorIntentType.CUSTOM_DIRECTION, None, "推进线程")
    constraints = (DirectorConstraint("c", intent, None, .6),)
    finder = DirectorPathFinder(Evaluator())
    # The custom scorer contract is wired into every returned path's score.
    paths = finder.find_paths(intent, constraints=constraints)
    assert paths and all(path.constraint_score == .1 for path in paths)
    assert paths[0].score <= 1
