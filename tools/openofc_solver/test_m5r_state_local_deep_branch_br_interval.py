from __future__ import annotations

import pytest

from deepofc.hu_two_round_br import exact_best_response
from deepofc.hu_two_round_joker import HUTwoRoundJokerSubgame
from m5r_deep_branch_br_interval import deep_branch_best_response_interval
from m5r_full_game_remainder_envelope import GLOBAL_RAW_POINT_ABS_BOUND
from m5r_state_local_deep_branch_br_interval import (
    state_local_deep_branch_best_response_interval,
)


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


@pytest.mark.parametrize("player", (0, 1))
def test_zero_threshold_state_local_collapses_to_exact(player: int) -> None:
    game = HUTwoRoundJokerSubgame()
    profile = _dominant_full_support_profile(game)
    p0_value = game.expected_u0(profile)
    exact = exact_best_response(game, profile, player).value

    result = state_local_deep_branch_best_response_interval(
        game,
        profile,
        player,
        profile_p0_value=p0_value,
        prune_reach_threshold=0.0,
    )

    assert abs(result.interval_width) <= 1e-12
    assert abs(result.lower_br_value - exact) <= 1e-10
    assert result.resolved_terminal_histories == game.terminal_count()
    assert result.skipped_terminal_histories == 0
    assert result.local_envelope_calls == 0


@pytest.mark.parametrize("player", (0, 1))
def test_state_local_pruning_contains_exact_and_tightens_global_scoring_envelope(
    player: int,
) -> None:
    game = HUTwoRoundJokerSubgame()
    profile = _dominant_full_support_profile(game)
    p0_value = game.expected_u0(profile)
    exact = exact_best_response(game, profile, player).value
    exact_gain = exact - (p0_value if player == 0 else -p0_value)
    threshold = game.chance_probability * 0.01

    global_result = deep_branch_best_response_interval(
        game,
        profile,
        player,
        profile_p0_value=p0_value,
        p0_utility_min=-float(GLOBAL_RAW_POINT_ABS_BOUND),
        p0_utility_max=float(GLOBAL_RAW_POINT_ABS_BOUND),
        prune_reach_threshold=threshold,
    )
    local_result = state_local_deep_branch_best_response_interval(
        game,
        profile,
        player,
        profile_p0_value=p0_value,
        prune_reach_threshold=threshold,
    )

    _assert_contains(local_result, exact, exact_gain)
    assert local_result.resolved_terminal_histories == global_result.resolved_terminal_histories
    assert local_result.skipped_terminal_histories == global_result.skipped_terminal_histories
    assert local_result.total_terminal_histories_accounted == game.terminal_count()
    assert local_result.local_envelope_calls > 0
    assert local_result.max_local_p0_width is not None
    assert local_result.max_local_p0_width < 2 * GLOBAL_RAW_POINT_ABS_BOUND
    assert local_result.interval_width < global_result.interval_width


def test_full_threshold_uses_post_round3_local_envelopes_and_contains_exact() -> None:
    game = HUTwoRoundJokerSubgame()
    profile = _dominant_full_support_profile(game)
    p0_value = game.expected_u0(profile)
    exact = exact_best_response(game, profile, 0).value
    exact_gain = exact - p0_value

    result = state_local_deep_branch_best_response_interval(
        game,
        profile,
        0,
        profile_p0_value=p0_value,
        prune_reach_threshold=game.chance_probability,
    )

    _assert_contains(result, exact, exact_gain)
    assert result.resolved_terminal_histories == 0
    assert result.skipped_terminal_histories == game.terminal_count()
    assert result.pruned_round3_prefixes > 0
    assert result.pruned_round4_opponent_branches == 0
    assert result.pruned_terminal_opponent_actions == 0
    assert result.local_envelope_calls == result.pruned_round3_prefixes
    assert result.interval_width > 0.0


def test_state_local_rejects_invalid_threshold() -> None:
    game = HUTwoRoundJokerSubgame()
    with pytest.raises(ValueError):
        state_local_deep_branch_best_response_interval(
            game,
            game.uniform_profile(),
            0,
            profile_p0_value=0.0,
            prune_reach_threshold=-1e-6,
        )
