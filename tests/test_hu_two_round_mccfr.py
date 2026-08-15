from deepofc.hu_two_round import HUTwoRoundSubgame
from deepofc.hu_two_round_mccfr import TwoRoundExternalSamplingMCCFR


def _max_profile_difference(left, right):
    worst = 0.0
    for info, left_dist in left.items():
        right_dist = right[info]
        for action, probability in left_dist.items():
            worst = max(worst, abs(probability - right_dist[action]))
    return worst


def test_deep_external_sampling_first_iteration_average_is_policy_actually_used():
    game = HUTwoRoundSubgame()
    solver = TwoRoundExternalSamplingMCCFR(game, seed=7)
    uniform = game.uniform_profile()
    solver.run(1)
    assert _max_profile_difference(
        solver.behavioral_time_average_profile(), uniform
    ) < 1e-15


def test_deep_external_sampling_is_seed_deterministic():
    game = HUTwoRoundSubgame()
    left = TwoRoundExternalSamplingMCCFR(game, seed=12345)
    right = TwoRoundExternalSamplingMCCFR(game, seed=12345)
    left.run(10)
    right.run(10)
    assert left.regrets == right.regrets
    assert left.local_active_since == right.local_active_since
    assert left.local_strategy_sum == right.local_strategy_sum
