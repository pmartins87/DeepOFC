from __future__ import annotations

import math

import pytest

from deepofc.hu_two_round_joker import HUTwoRoundJokerSubgame
from deepofc.hu_two_round_mccfr import TwoRoundExternalSamplingMCCFR
from m5q_exploration_support_floor import (
    evaluate_exploration_floor,
    uniform_exploration_mix,
)


def _base_profile():
    game = HUTwoRoundJokerSubgame()
    solver = TwoRoundExternalSamplingMCCFR(game, seed=2026090201)
    solver.run(16)
    return game, solver.current_profile()


def test_any_positive_uniform_exploration_restores_full_support() -> None:
    game, base = _base_profile()
    for epsilon in (0.01, 0.10, 1.0):
        row = evaluate_exploration_floor(
            game,
            base,
            epsilon=epsilon,
            utility_range=4.0,
            target_exploitability=0.15,
            probe_iterations=1_000_000,
        )
        assert row.zero_probability_histories == 0
        assert row.global_sampling_floor > 0.0
        assert row.appendix_c_required_iterations_for_target > 0


def test_epsilon_one_is_exact_uniform_profile() -> None:
    game, base = _base_profile()
    mixed = uniform_exploration_mix(game, base, epsilon=1.0)
    uniform = game.uniform_profile()
    for info, actions in game.info_actions.items():
        for action in actions:
            assert math.isclose(mixed[info][action], uniform[info][action])


def test_larger_epsilon_does_not_reduce_observed_min_support_on_frozen_surface() -> None:
    game, base = _base_profile()
    small = evaluate_exploration_floor(
        game,
        base,
        epsilon=0.01,
        utility_range=4.0,
        target_exploitability=0.15,
        probe_iterations=1_000_000,
    )
    full = evaluate_exploration_floor(
        game,
        base,
        epsilon=1.0,
        utility_range=4.0,
        target_exploitability=0.15,
        probe_iterations=1_000_000,
    )
    assert full.global_sampling_floor >= small.global_sampling_floor


def test_invalid_epsilon_fails_closed() -> None:
    game, base = _base_profile()
    for epsilon in (0.0, -0.01, 1.01):
        with pytest.raises(ValueError):
            uniform_exploration_mix(game, base, epsilon=epsilon)
