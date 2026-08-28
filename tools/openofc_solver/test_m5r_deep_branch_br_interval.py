from __future__ import annotations

import pytest

from deepofc.hu_two_round_br import exact_best_response
from deepofc.hu_two_round_joker import HUTwoRoundJokerSubgame
from m5q_support_range_feasibility import exact_terminal_utility_range
from m5r_deep_branch_br_interval import deep_branch_best_response_interval
from m5r_prefix_subtree_br_interval import prefix_subtree_best_response_interval


def _dominant_full_support_profile(game, dominant_mass: float = 0.8):
    profile = {}
    for info, actions in game.info_actions.items():
        ordered = tuple(sorted(actions, key=lambda action: action.key()))
        if len(ordered) == 1:
            profile[info] = {ordered[0]: 1.0}
            continue
        tail = (1.0 - dominant_mass) / (len(ordered) - 1)
        profile[info] = {
            action: dominant_mass if index == 0 else tail
            for index, action in enumerate(ordered)
        }
    return profile


def _assert_contains(result, exact_br: float, exact_gain: float) -> None:
    assert result.lower_br_value <= exact_br + 1e-10
    assert exact_br <= result.upper_br_value + 1e-10
    assert result.lower_deviation_gain <= exact_gain + 1e-10
    assert exact_gain <= result.upper_deviation_gain + 1e-10


def test_zero_threshold_deep_branch_collapses_to_exact() -> None:
    game = HUTwoRoundJokerSubgame()
    profile = _dominant_full_support_profile(game)
    utility = exact_terminal_utility_range(game)
    p0_value = game.expected_u0(profile)
    exact = exact_best_response(game, profile, 0).value

    result = deep_branch_best_response_interval(
        game,
        profile,
        0,
        profile_p0_value=p0_value,
        p0_utility_min=utility.minimum_p0_utility,
        p0_utility_max=utility.maximum_p0_utility,
        prune_reach_threshold=0.0,
    )

    assert abs(result.interval_width) <= 1e-12
    assert abs(result.lower_br_value - exact) <= 1e-10
    assert result.resolved_terminal_histories == game.terminal_count()
    assert result.skipped_terminal_histories == 0
    assert result.total_terminal_histories_accounted == game.terminal_count()


def test_full_threshold_deep_branch_skips_every_terminal_and_contains_exact() -> None:
    game = HUTwoRoundJokerSubgame()
    profile = _dominant_full_support_profile(game)
    utility = exact_terminal_utility_range(game)
    p0_value = game.expected_u0(profile)
    exact = exact_best_response(game, profile, 1).value
    exact_gain = exact + p0_value

    result = deep_branch_best_response_interval(
        game,
        profile,
        1,
        profile_p0_value=p0_value,
        p0_utility_min=utility.minimum_p0_utility,
        p0_utility_max=utility.maximum_p0_utility,
        prune_reach_threshold=game.chance_probability,
    )

    _assert_contains(result, exact, exact_gain)
    assert result.resolved_terminal_histories == 0
    assert result.skipped_terminal_histories == game.terminal_count()
    assert result.interval_width > 0.0


def test_deeper_pruning_saves_work_below_prefix_only_granularity() -> None:
    game = HUTwoRoundJokerSubgame()
    profile = _dominant_full_support_profile(game)
    utility = exact_terminal_utility_range(game)
    p0_value = game.expected_u0(profile)
    exact = exact_best_response(game, profile, 0).value
    exact_gain = exact - p0_value
    threshold = game.chance_probability * 0.01

    prefix = prefix_subtree_best_response_interval(
        game,
        profile,
        0,
        profile_p0_value=p0_value,
        p0_utility_min=utility.minimum_p0_utility,
        p0_utility_max=utility.maximum_p0_utility,
        prune_reach_threshold=threshold,
    )
    deep = deep_branch_best_response_interval(
        game,
        profile,
        0,
        profile_p0_value=p0_value,
        p0_utility_min=utility.minimum_p0_utility,
        p0_utility_max=utility.maximum_p0_utility,
        prune_reach_threshold=threshold,
    )

    _assert_contains(deep, exact, exact_gain)
    assert prefix.resolved_terminal_histories == game.terminal_count()
    assert deep.resolved_terminal_histories < prefix.resolved_terminal_histories
    assert deep.skipped_terminal_histories > 0
    assert (
        deep.pruned_round4_opponent_branches
        + deep.pruned_terminal_opponent_actions
        > 0
    )
    assert deep.total_terminal_histories_accounted == game.terminal_count()


def test_deep_branch_rejects_invalid_threshold() -> None:
    game = HUTwoRoundJokerSubgame()
    with pytest.raises(ValueError):
        deep_branch_best_response_interval(
            game,
            game.uniform_profile(),
            0,
            profile_p0_value=0.0,
            p0_utility_min=-2.0,
            p0_utility_max=2.0,
            prune_reach_threshold=-1e-6,
        )
