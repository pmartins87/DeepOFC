from deepofc.hu_two_round import HUTwoRoundSubgame
from deepofc.hu_two_round_outcome_mccfr import TwoRoundOutcomeSamplingMCCFR


def test_outcome_sampling_is_seed_deterministic_and_touches_two_terminals_per_iteration():
    game = HUTwoRoundSubgame()
    left = TwoRoundOutcomeSamplingMCCFR(game, seed=12345, epsilon=0.6)
    right = TwoRoundOutcomeSamplingMCCFR(game, seed=12345, epsilon=0.6)

    left.run(20)
    right.run(20)

    assert left.regrets == right.regrets
    assert left.training_terminal_evaluations == 40
    assert right.training_terminal_evaluations == 40


def test_outcome_sampling_exploration_keeps_every_legal_action_positive():
    game = HUTwoRoundSubgame()
    solver = TwoRoundOutcomeSamplingMCCFR(game, seed=7, epsilon=0.6)
    info = next(iter(game.info_actions))
    current = solver._distribution(info)
    sampling = solver._sampling_distribution(info, info.player, current)
    assert set(sampling) == set(game.actions(info))
    assert all(probability > 0.0 for probability in sampling.values())
    assert abs(sum(sampling.values()) - 1.0) < 1e-12
