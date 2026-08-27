from __future__ import annotations

from deepofc.hu_two_round_joker import HUTwoRoundJokerSubgame
from deepofc.hu_two_round_mccfr import TwoRoundExternalSamplingMCCFR
from m5q_predictable_freedman_trajectory import (
    AUTHORITY,
    PredictableVarianceExternalSamplingMCCFR,
)


def _max_regret_difference(a, b) -> float:
    worst = 0.0
    for info in a:
        for action in a[info]:
            worst = max(worst, abs(float(a[info][action]) - float(b[info][action])))
    return worst


def test_predictable_instrumentation_preserves_sampled_training_trajectory() -> None:
    game = HUTwoRoundJokerSubgame()
    seed = 2026090511
    plain = TwoRoundExternalSamplingMCCFR(game, seed=seed)
    instrumented = PredictableVarianceExternalSamplingMCCFR(game, seed=seed)

    plain.run(3)
    instrumented.run(3)

    assert plain.iteration == instrumented.iteration == 3
    assert instrumented.predictable_accounted_iterations == 3
    assert _max_regret_difference(plain.regrets, instrumented.regrets) == 0.0
    assert plain.rng.getstate() == instrumented.rng.getstate()


def test_predictable_visit_mass_accumulates_with_iteration_alignment() -> None:
    game = HUTwoRoundJokerSubgame()
    solver = PredictableVarianceExternalSamplingMCCFR(game, seed=2026090529)
    solver.run(4)

    for player in (0, 1):
        round3_mass = sum(
            value
            for info, value in solver.predictable_visit_sum.items()
            if info.player == player and info.round_index == 3
        )
        round4_mass = sum(
            value
            for info, value in solver.predictable_visit_sum.items()
            if info.player == player and info.round_index == 4
        )
        assert abs(round3_mass - 4.0) <= 1e-10
        assert abs(round4_mass - 36.0) <= 1e-10


def test_freedman_regret_bound_is_finite_monotone_over_sampled_term_and_noncertifying() -> None:
    game = HUTwoRoundJokerSubgame()
    solver = PredictableVarianceExternalSamplingMCCFR(game, seed=2026090547)
    solver.run(4)
    bound = solver.regret_bound(utility_range=4.0, familywise_failure_probability=0.05)

    assert bound.iterations == 4
    assert bound.action_coordinates == 39456
    assert bound.exploitability_upper >= bound.sampled_positive_regret_exploitability >= 0.0
    assert bound.concentration_additive_exploitability >= 0.0
    assert bound.maximum_coordinate_predictable_variation > 0.0
    assert bound.total_coordinate_predictable_variation > 0.0
    assert bound.authority == AUTHORITY
    assert bound.production_certification_eligible is False
    assert bound.real_routes_certified == 0
