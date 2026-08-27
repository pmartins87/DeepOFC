from __future__ import annotations

from deepofc.hu_two_round_joker import HUTwoRoundJokerSubgame
from m5q_support_range_feasibility import (
    exact_terminal_utility_range,
    external_sampling_support_report,
)


def test_exact_joker_terminal_range_is_finite_and_nontrivial() -> None:
    game = HUTwoRoundJokerSubgame()
    report = exact_terminal_utility_range(game)
    assert report.terminal_histories > 0
    assert report.minimum_p0_utility < report.maximum_p0_utility
    assert report.utility_range == report.maximum_p0_utility - report.minimum_p0_utility


def test_uniform_profile_has_positive_external_sampling_support() -> None:
    game = HUTwoRoundJokerSubgame()
    report = external_sampling_support_report(
        game, game.uniform_profile(), profile_id="uniform-test"
    )
    for support in (report.player0_traverser, report.player1_traverser):
        assert support.terminal_histories > 0
        assert support.zero_probability_histories == 0
        assert support.minimum_sampling_probability > 0.0
        assert support.minimum_positive_sampling_probability is not None
        assert support.has_strictly_positive_global_floor
    assert report.payload()["production_certification_eligible"] is False
    assert report.payload()["real_routes_certified"] == 0


def test_zero_probability_opponent_action_collapses_global_floor_for_other_traverser() -> None:
    game = HUTwoRoundJokerSubgame()
    profile = game.uniform_profile()
    target = next(info for info in game.info_actions if info.player == 1)
    actions = game.actions(target)
    assert len(actions) >= 2
    chosen = actions[0]
    profile[target] = {action: 1.0 if action == chosen else 0.0 for action in actions}

    report = external_sampling_support_report(game, profile, profile_id="zero-support-test")
    assert report.player0_traverser.zero_probability_histories > 0
    assert report.player0_traverser.minimum_sampling_probability == 0.0
    assert not report.player0_traverser.has_strictly_positive_global_floor
