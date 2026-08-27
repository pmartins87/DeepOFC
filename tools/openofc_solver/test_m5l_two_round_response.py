from __future__ import annotations

import math

import pytest

from deepofc.hu_two_round import HUTwoRoundSubgame
from deepofc.hu_two_round_br import TwoRoundBestResponse
from m5l_two_round_response import (
    AUTHORITY,
    TwoRoundOutcomeSampledResponseLearner,
)


def _uniform_profile():
    # HUTwoRoundSubgame treats a missing infoset as uniform, exactly as the
    # three-round Q0/Q1 benchmark does for its canonical uniform profile.
    return {}


def _fixture_reference(game: HUTwoRoundSubgame, player: int) -> TwoRoundBestResponse:
    choices = {
        info: min(actions, key=lambda action: action.key())
        for info, actions in game.info_actions.items()
        if info.player == player
    }
    return TwoRoundBestResponse(player=player, value=0.0, choices=choices)


def test_two_round_response_trains_deterministically_and_preserves_full_response_surface() -> None:
    game = HUTwoRoundSubgame()
    first = TwoRoundOutcomeSampledResponseLearner(
        game,
        _uniform_profile(),
        deviator_player=0,
        epsilon=0.6,
        seed=2026083001,
    )
    second = TwoRoundOutcomeSampledResponseLearner(
        game,
        _uniform_profile(),
        deviator_player=0,
        epsilon=0.6,
        seed=2026083001,
    )
    first_report = first.run_to(16)
    second_report = second.run_to(16)
    assert first_report == second_report
    assert first_report.authority == AUTHORITY
    assert first_report.iterations == 16
    assert first_report.terminal_evaluations == 16
    assert first_report.infosets > 0
    assert first_report.total_visits > 0
    assert set(first.nodes) == set(second.nodes)
    for info in first.nodes:
        assert first.nodes[info].regrets == second.nodes[info].regrets
        assert first.nodes[info].cumulative_policy == second.nodes[info].cumulative_policy

    reference = _fixture_reference(game, 0)
    pure, learned, fallback = first.pure_response(reference)
    assert set(pure.choices) == set(reference.choices)
    assert learned + fallback == len(reference.choices)
    assert learned > 0


def test_two_round_response_supports_both_persistent_players() -> None:
    game = HUTwoRoundSubgame()
    for player in (0, 1):
        learner = TwoRoundOutcomeSampledResponseLearner(
            game,
            _uniform_profile(),
            deviator_player=player,
            epsilon=0.6,
            seed=2026083011 + player,
        )
        report = learner.run_to(8)
        assert report.persistent_player == player
        assert report.infosets > 0
        reference = _fixture_reference(game, player)
        pure, learned, fallback = learner.pure_response(reference)
        assert pure.player == player
        assert learned + fallback == len(reference.choices)


def test_two_round_response_rejects_invalid_inputs_and_reference_player_mismatch() -> None:
    game = HUTwoRoundSubgame()
    with pytest.raises(ValueError, match="P0 or P1"):
        TwoRoundOutcomeSampledResponseLearner(
            game, _uniform_profile(), deviator_player=2
        )
    with pytest.raises(ValueError, match="epsilon"):
        TwoRoundOutcomeSampledResponseLearner(
            game, _uniform_profile(), deviator_player=0, epsilon=0.0
        )

    learner = TwoRoundOutcomeSampledResponseLearner(
        game, _uniform_profile(), deviator_player=0, seed=99
    )
    learner.run_to(1)
    with pytest.raises(ValueError, match="player mismatch"):
        learner.pure_response(_fixture_reference(game, 1))


def test_average_response_probabilities_are_finite_and_normalized() -> None:
    game = HUTwoRoundSubgame()
    learner = TwoRoundOutcomeSampledResponseLearner(
        game, _uniform_profile(), deviator_player=1, seed=2026083021
    )
    learner.run_to(24)
    for node in learner.nodes.values():
        distribution = node.average_policy()
        assert set(distribution) == set(node.actions)
        assert all(math.isfinite(value) and value >= 0.0 for value in distribution.values())
        assert abs(sum(distribution.values()) - 1.0) <= 1e-12
