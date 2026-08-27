from __future__ import annotations

from deepofc.hu_two_round_cfr import TwoRoundFullTreeCFR
from deepofc.hu_two_round_joker import HUTwoRoundJokerSubgame
from deepofc.hu_two_round_mccfr import TwoRoundExternalSamplingMCCFR
from m5q_external_sampling_unbiasedness import frozen_regret_table
from m5q_reach_weighted_mccfr_average import (
    AUTHORITY,
    ReachWeightedAverageExternalSamplingMCCFR,
)


def _copy(table):
    return {
        info: {action: float(value) for action, value in values.items()}
        for info, values in table.items()
    }


def _max_profile_difference(a, b) -> float:
    worst = 0.0
    for info in a:
        for action in a[info]:
            worst = max(worst, abs(float(a[info][action]) - float(b[info][action])))
    return worst


def _max_regret_difference(a, b) -> float:
    worst = 0.0
    for info in a:
        for action in a[info]:
            worst = max(worst, abs(float(a[info][action]) - float(b[info][action])))
    return worst


def test_one_step_average_matches_full_tree_reference_semantics() -> None:
    game = HUTwoRoundJokerSubgame()
    frozen = frozen_regret_table(game, "hash-mixed")

    reference = TwoRoundFullTreeCFR(game, variant="cfr")
    reference.regrets = _copy(frozen)

    candidate = ReachWeightedAverageExternalSamplingMCCFR(game, seed=73)
    candidate.regrets = _copy(frozen)

    reference.step()
    candidate.step()

    assert candidate.reach_weighted_recorded_iterations == 1
    assert _max_profile_difference(
        reference.average_profile(), candidate.reach_weighted_average_profile()
    ) <= 1e-15


def test_average_instrumentation_does_not_change_sampled_regret_trajectory() -> None:
    game = HUTwoRoundJokerSubgame()
    seed = 2026090411
    plain = TwoRoundExternalSamplingMCCFR(game, seed=seed)
    candidate = ReachWeightedAverageExternalSamplingMCCFR(game, seed=seed)

    plain.run(3)
    candidate.run(3)

    assert plain.iteration == candidate.iteration == 3
    assert _max_regret_difference(plain.regrets, candidate.regrets) == 0.0
    assert plain.rng.getstate() == candidate.rng.getstate()
    assert candidate.reach_weighted_recorded_iterations == 3


def test_reach_weighted_average_is_not_mislabeled_local_time_average() -> None:
    game = HUTwoRoundJokerSubgame()
    candidate = ReachWeightedAverageExternalSamplingMCCFR(game, seed=2026090429)
    candidate.run(4)

    reach_weighted = candidate.reach_weighted_average_profile()
    local_time = candidate.behavioral_time_average_profile()

    assert _max_profile_difference(reach_weighted, local_time) > 0.0
    status = candidate.reach_weighted_average_status()
    assert status.recorded_iterations == 4
    assert status.authority == AUTHORITY
    assert status.production_certification_eligible is False
    assert status.real_routes_certified == 0
