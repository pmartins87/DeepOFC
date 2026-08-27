from __future__ import annotations

import math

import pytest

from deepofc.hu_two_round_joker import HUTwoRoundJokerSubgame
from m5p_external_sampling_theoretical_bound import (
    AUTHORITY,
    external_sampling_theoretical_bound,
    player_sequence_structure,
    project_raw_pairwise_utility_abs_bound,
    project_raw_pairwise_utility_range,
    required_iterations_for_exploitability,
)


def test_project_raw_pairwise_range_is_derived_conservative_206() -> None:
    assert project_raw_pairwise_utility_abs_bound() == 103.0
    assert project_raw_pairwise_utility_range() == 206.0


def test_joker_sequence_accounting_is_symmetric_and_nonempty() -> None:
    game = HUTwoRoundJokerSubgame()
    p0 = player_sequence_structure(game, 0)
    p1 = player_sequence_structure(game, 1)
    assert p0.infosets == p1.infosets
    assert p0.prefix_groups == p1.prefix_groups
    assert p0.own_action_sequences == p1.own_action_sequences
    assert p0.m_value == pytest.approx(p1.m_value, abs=1e-12)
    assert p0.infosets > 0
    assert p0.prefix_groups > 1
    assert p0.own_action_sequences > p0.prefix_groups
    assert p0.largest_prefix_group > 0


def test_theorem_bound_has_joint_confidence_and_inverse_sqrt_scaling() -> None:
    game = HUTwoRoundJokerSubgame()
    b100 = external_sampling_theoretical_bound(
        game, iterations=100, overall_failure_probability=0.05, utility_range=1.0
    )
    b400 = external_sampling_theoretical_bound(
        game, iterations=400, overall_failure_probability=0.05, utility_range=1.0
    )
    assert b100.authority == AUTHORITY
    assert b100.joint_confidence == pytest.approx(0.95)
    assert b100.per_player_failure_probability == pytest.approx(0.025)
    assert b400.exploitability_upper_bound == pytest.approx(
        0.5 * b100.exploitability_upper_bound, rel=1e-12
    )
    assert b100.nash_conv_upper_bound == pytest.approx(
        2.0 * b100.exploitability_upper_bound, rel=1e-12
    )
    assert b100.sha256 and len(b100.sha256) == 64


def test_required_iterations_rounds_up_to_requested_bound() -> None:
    game = HUTwoRoundJokerSubgame()
    target = 0.15
    required = required_iterations_for_exploitability(
        game,
        target_exploitability=target,
        overall_failure_probability=0.05,
        utility_range=1.0,
    )
    assert required > 1
    at_required = external_sampling_theoretical_bound(
        game,
        iterations=required,
        overall_failure_probability=0.05,
        utility_range=1.0,
    )
    assert at_required.exploitability_upper_bound <= target + 1e-12
    previous = external_sampling_theoretical_bound(
        game,
        iterations=required - 1,
        overall_failure_probability=0.05,
        utility_range=1.0,
    )
    assert previous.exploitability_upper_bound > target - 1e-12


def test_fail_closed_inputs() -> None:
    game = HUTwoRoundJokerSubgame()
    with pytest.raises(ValueError):
        external_sampling_theoretical_bound(game, iterations=0)
    with pytest.raises(ValueError):
        external_sampling_theoretical_bound(
            game, iterations=1, overall_failure_probability=0.0
        )
    with pytest.raises(ValueError):
        external_sampling_theoretical_bound(game, iterations=1, utility_range=0.0)
    with pytest.raises(ValueError):
        required_iterations_for_exploitability(game, target_exploitability=math.nan)
