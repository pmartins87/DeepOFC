from deepofc.hu_mccfr import ExternalSamplingMCCFR
from deepofc.hu_subgame import HUFinalRoundSubgame


def _assert_profile(game, profile):
    assert set(profile) == set(game.info_actions)
    for info, actions in game.info_actions.items():
        dist = profile[info]
        assert set(dist) == set(actions)
        assert all(value >= 0.0 for value in dist.values())
        assert abs(sum(dist.values()) - 1.0) < 1e-12


def test_first_completed_iteration_averages_the_strategy_that_was_actually_used():
    game = HUFinalRoundSubgame()
    solver = ExternalSamplingMCCFR(game, seed=7)
    initial = game.uniform_profile()
    solver.run(1)

    # Regrets may already have changed, but iteration 1 was traversed entirely
    # with the initial uniform strategy. Therefore its time-average must be
    # exactly uniform, not the post-update regret-matching strategy.
    assert solver.average_profile() == initial


def test_external_sampling_is_seed_deterministic_and_profiles_remain_valid():
    game = HUFinalRoundSubgame()
    left = ExternalSamplingMCCFR(game, seed=12345)
    right = ExternalSamplingMCCFR(game, seed=12345)
    left.run(25)
    right.run(25)

    assert left.regrets == right.regrets
    assert left.active_since == right.active_since
    assert left.strategy_sum == right.strategy_sum
    _assert_profile(game, left.current_profile())
    _assert_profile(game, left.average_profile())
