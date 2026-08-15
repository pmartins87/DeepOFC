from deepofc.hu_two_round import HUTwoRoundSubgame
from deepofc.hu_two_round_mccfr_reach_average import (
    TwoRoundExternalSamplingReachAverage,
)


def test_reach_weighted_average_after_first_iteration_is_uniform_policy_used():
    game = HUTwoRoundSubgame()
    solver = TwoRoundExternalSamplingReachAverage(game, seed=7)
    uniform = game.uniform_profile()
    solver.run(1)
    assert solver.cfr_average_profile() == uniform
