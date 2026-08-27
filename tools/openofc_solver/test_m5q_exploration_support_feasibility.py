from __future__ import annotations

import math

import pytest

from deepofc.hu_two_round_joker import HUTwoRoundJokerSubgame
from m5q_exploration_support_feasibility import (
    AUTHORITY,
    exploration_structural_support_report,
)
from m5q_support_range_feasibility import external_sampling_support_report


def test_epsilon_one_matches_exact_uniform_external_sampling_support() -> None:
    game = HUTwoRoundJokerSubgame()
    structural = exploration_structural_support_report(game, 1.0)
    exact = external_sampling_support_report(
        game, game.uniform_profile(), profile_id="uniform"
    )
    assert structural.authority == AUTHORITY
    assert structural.global_sampling_probability_floor > 0.0
    assert math.isclose(
        structural.player0.minimum_structural_sampling_probability,
        exact.player0_traverser.minimum_sampling_probability,
        rel_tol=0.0,
        abs_tol=1e-18,
    )
    assert math.isclose(
        structural.player1.minimum_structural_sampling_probability,
        exact.player1_traverser.minimum_sampling_probability,
        rel_tol=0.0,
        abs_tol=1e-18,
    )
    assert structural.player0.maximum_sampled_decisions == 2
    assert structural.player1.maximum_sampled_decisions == 2


def test_two_sampled_opponent_decisions_make_floor_scale_as_epsilon_squared() -> None:
    game = HUTwoRoundJokerSubgame()
    baseline = exploration_structural_support_report(game, 1.0)
    for epsilon in (0.5, 0.2, 0.1, 0.01):
        report = exploration_structural_support_report(game, epsilon)
        expected = baseline.global_sampling_probability_floor * epsilon * epsilon
        assert math.isclose(
            report.global_sampling_probability_floor,
            expected,
            rel_tol=1e-12,
            abs_tol=0.0,
        )


def test_report_is_deterministic_and_firewalled() -> None:
    game = HUTwoRoundJokerSubgame()
    first = exploration_structural_support_report(game, 0.1)
    second = exploration_structural_support_report(game, 0.1)
    assert first == second
    payload = first.payload()
    assert payload["production_solver_modified"] is False
    assert payload["production_certification_eligible"] is False
    assert payload["real_routes_certified"] == 0
    assert payload["sha256"]


@pytest.mark.parametrize("epsilon", [0.0, -0.1, 1.000001, float("inf"), float("nan")])
def test_invalid_epsilon_fails_closed(epsilon: float) -> None:
    with pytest.raises(ValueError):
        exploration_structural_support_report(HUTwoRoundJokerSubgame(), epsilon)
