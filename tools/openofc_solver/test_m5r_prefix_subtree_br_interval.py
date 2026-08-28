from __future__ import annotations

import math

import pytest

from deepofc.hu_two_round_br import exact_best_response
from deepofc.hu_two_round_joker import HUTwoRoundJokerSubgame
from m5q_support_range_feasibility import exact_terminal_utility_range
from m5r_prefix_subtree_br_interval import prefix_subtree_best_response_interval


def _geometric_profile(game, decay: float = 0.2):
    profile = {}
    for info, actions in game.info_actions.items():
        ordered = tuple(sorted(actions, key=lambda action: action.key()))
        raw = [decay**index for index in range(len(ordered))]
        total = sum(raw)
        profile[info] = {
            action: raw[index] / total
            for index, action in enumerate(ordered)
        }
    return profile


def _assert_contains(result, exact_value: float, exact_gain: float) -> None:
    assert result.lower_br_value <= exact_value + 1e-10
    assert exact_value <= result.upper_br_value + 1e-10
    assert result.lower_deviation_gain <= exact_gain + 1e-10
    assert exact_gain <= result.upper_deviation_gain + 1e-10


def test_zero_threshold_uniform_collapses_to_exact_joker() -> None:
    game = HUTwoRoundJokerSubgame()
    profile = game.uniform_profile()
    p0_value = game.expected_u0(profile)
    utility = exact_terminal_utility_range(game)
    exact = exact_best_response(game, profile, 0).value

    result = prefix_subtree_best_response_interval(
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
    assert abs(result.upper_br_value - exact) <= 1e-10
    assert result.pruned_round3_prefixes == 0
    assert result.skipped_terminal_histories == 0
    assert result.resolved_terminal_histories == game.terminal_count()
    assert result.total_terminal_histories_accounted == game.terminal_count()
    assert abs(result.terminal_work_fraction - 1.0) <= 1e-12


def test_full_prefix_prune_skips_every_terminal_and_contains_exact() -> None:
    game = HUTwoRoundJokerSubgame()
    profile = game.uniform_profile()
    p0_value = game.expected_u0(profile)
    utility = exact_terminal_utility_range(game)
    exact = exact_best_response(game, profile, 1).value
    own_profile = -p0_value

    result = prefix_subtree_best_response_interval(
        game,
        profile,
        1,
        profile_p0_value=p0_value,
        p0_utility_min=utility.minimum_p0_utility,
        p0_utility_max=utility.maximum_p0_utility,
        prune_reach_threshold=game.chance_probability,
    )

    _assert_contains(result, exact, exact - own_profile)
    assert result.resolved_terminal_histories == 0
    assert result.skipped_terminal_histories == game.terminal_count()
    assert result.pruned_round3_prefixes > 0
    assert abs(result.terminal_work_fraction) <= 1e-12
    assert result.interval_width > 0.0


def test_geometric_profile_threshold_reduces_work_monotonically() -> None:
    game = HUTwoRoundJokerSubgame()
    profile = _geometric_profile(game)
    p0_value = game.expected_u0(profile)
    utility = exact_terminal_utility_range(game)
    exact = exact_best_response(game, profile, 0).value
    exact_gain = exact - p0_value
    cp = game.chance_probability

    low = prefix_subtree_best_response_interval(
        game,
        profile,
        0,
        profile_p0_value=p0_value,
        p0_utility_min=utility.minimum_p0_utility,
        p0_utility_max=utility.maximum_p0_utility,
        prune_reach_threshold=cp * 0.02,
    )
    high = prefix_subtree_best_response_interval(
        game,
        profile,
        0,
        profile_p0_value=p0_value,
        p0_utility_min=utility.minimum_p0_utility,
        p0_utility_max=utility.maximum_p0_utility,
        prune_reach_threshold=cp * 0.20,
    )

    _assert_contains(low, exact, exact_gain)
    _assert_contains(high, exact, exact_gain)
    assert high.resolved_terminal_histories < low.resolved_terminal_histories
    assert high.skipped_terminal_histories > low.skipped_terminal_histories
    assert high.terminal_work_fraction < low.terminal_work_fraction
    assert high.interval_width + 1e-10 >= low.interval_width
    assert high.resolved_terminal_histories > 0
    assert high.skipped_terminal_histories > 0
    assert low.total_terminal_histories_accounted == game.terminal_count()
    assert high.total_terminal_histories_accounted == game.terminal_count()


def test_prefix_interval_rejects_invalid_inputs() -> None:
    game = HUTwoRoundJokerSubgame()
    profile = game.uniform_profile()
    with pytest.raises(ValueError):
        prefix_subtree_best_response_interval(
            game,
            profile,
            0,
            profile_p0_value=0.0,
            p0_utility_min=-2.0,
            p0_utility_max=2.0,
            prune_reach_threshold=-1e-9,
        )
    with pytest.raises(ValueError):
        prefix_subtree_best_response_interval(
            game,
            profile,
            2,
            profile_p0_value=0.0,
            p0_utility_min=-2.0,
            p0_utility_max=2.0,
            prune_reach_threshold=0.0,
        )
    with pytest.raises(ValueError):
        prefix_subtree_best_response_interval(
            game,
            profile,
            0,
            profile_p0_value=math.nan,
            p0_utility_min=-2.0,
            p0_utility_max=2.0,
            prune_reach_threshold=0.0,
        )
