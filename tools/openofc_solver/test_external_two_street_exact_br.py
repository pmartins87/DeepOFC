from __future__ import annotations

import math

import pytest

from external_two_street_counterfactual_resolve import build_reachable_infoset_support
from external_two_street_exact_br import (
    AUTHORITY,
    exact_best_response,
    exact_nash_conv,
    replay_best_response_value,
)
from test_external_two_street_infoset_search import _coherent_r3_state, _support_worlds


def _uniform_complete_profile(support):
    return {
        row.information_state_key: {
            action_key: 1.0 / len(row.action_keys) for action_key in row.action_keys
        }
        for row in support
    }


def test_exact_best_response_matches_independent_replay_for_both_players() -> None:
    worlds = _support_worlds()[:2]
    state = _coherent_r3_state(worlds[0])
    support = build_reachable_infoset_support(state, worlds)
    profile = _uniform_complete_profile(support)

    for player in (0, 1):
        br = exact_best_response(
            state,
            worlds,
            opponent_profile=profile,
            player=player,
            support_rows=support,
        )
        assert br.player == player
        assert br.round3_infosets > 0
        assert br.round4_infosets > 0
        assert len(br.choices) == sum(1 for row in support if row.actor == player)
        replay = replay_best_response_value(
            state,
            worlds,
            support_rows=support,
            opponent_profile=profile,
            response=br,
        )
        own_replay = replay.expected_u0 if player == 0 else -replay.expected_u0
        assert math.isclose(br.value, own_replay, rel_tol=1e-10, abs_tol=1e-10)


def test_exact_nash_conv_is_nonnegative_and_fails_closed_on_incomplete_opponent() -> None:
    worlds = _support_worlds()[:2]
    state = _coherent_r3_state(worlds[0])
    support = build_reachable_infoset_support(state, worlds)
    profile = _uniform_complete_profile(support)
    result = exact_nash_conv(
        state,
        worlds,
        profile=profile,
        support_rows=support,
    )
    assert result.nash_conv >= 0.0
    assert math.isclose(result.exploitability, 0.5 * result.nash_conv)

    with pytest.raises(ValueError, match="opponent profile incomplete"):
        exact_best_response(
            state,
            worlds,
            opponent_profile={},
            player=0,
            support_rows=support,
        )


def test_exact_br_authority_is_reduced_game_only() -> None:
    assert AUTHORITY == "EXACT_FINITE_SUPPORT_TWO_STREET_BR_REDUCED_GAME_ONLY"
