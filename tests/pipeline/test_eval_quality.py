"""Quality gate: fails CI if a change makes retrieval clearly worse.

The thresholds sit a little below the measured values (Hit@1 0.62, Hit@5 0.79
for the default hash embedder), so normal tuning passes and a real regression
does not.
"""
from eval.run_eval import run


def test_retrieval_quality_does_not_regress():
    result = run(backend="hash")
    assert result["hit@1"] >= 0.5
    assert result["hit@5"] >= 0.7
    assert result["mrr"] >= 0.55


def test_result_is_far_better_than_random_ranking():
    result = run(backend="hash")
    assert result["hit@1"] > 5 * result["random_hit@1"]
    assert result["hit@5"] > 2 * result["random_hit@5"]
