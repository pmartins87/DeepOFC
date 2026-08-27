from __future__ import annotations

import copy

import pytest

from deepofc.hu_two_round_joker import HUTwoRoundJokerSubgame
from m5q_external_sampling_unbiasedness import (
    InstrumentedTwoRoundExternalSamplingMCCFR,
    ProjectionMap,
    exact_full_tree_regret_delta,
    frozen_regret_table,
    profile_max_probability_difference,
)


def _training_state(solver: InstrumentedTwoRoundExternalSamplingMCCFR):
    return (
        solver.iteration,
        copy.deepcopy(solver.regrets),
        copy.deepcopy(solver.local_strategy_sum),
        copy.deepcopy(solver.local_active_since),
    )


@pytest.mark.parametrize("rule", ["uniform", "hash-mixed"])
def test_full_tree_and_external_sampling_share_frozen_regret_matching_profile(rule: str) -> None:
    game = HUTwoRoundJokerSubgame()
    table = frozen_regret_table(game, rule)
    assert profile_max_probability_difference(game, table) <= 1e-15


def test_sample_probe_mutates_only_rng_state() -> None:
    game = HUTwoRoundJokerSubgame()
    table = frozen_regret_table(game, "hash-mixed")
    solver = InstrumentedTwoRoundExternalSamplingMCCFR(game, seed=2026090101)
    solver.install_frozen_regrets(table)
    before = _training_state(solver)
    delta = solver.sample_regret_delta_pair()
    after = _training_state(solver)
    assert before == after
    assert delta
    assert all(info.player in (0, 1) for info in delta)


def test_same_seed_and_frozen_table_produce_same_probe() -> None:
    game = HUTwoRoundJokerSubgame()
    table = frozen_regret_table(game, "hash-mixed")
    left = InstrumentedTwoRoundExternalSamplingMCCFR(game, seed=2026090137)
    right = InstrumentedTwoRoundExternalSamplingMCCFR(game, seed=2026090137)
    left.install_frozen_regrets(table)
    right.install_frozen_regrets(table)
    assert left.sample_regret_delta_pair() == right.sample_regret_delta_pair()
    assert left.sample_regret_delta_pair() == right.sample_regret_delta_pair()


def test_exact_delta_and_projection_surface_are_complete_and_deterministic() -> None:
    game = HUTwoRoundJokerSubgame()
    exact_a = exact_full_tree_regret_delta(game, profile_rule="uniform")
    exact_b = exact_full_tree_regret_delta(game, profile_rule="uniform")
    projection = ProjectionMap(game, projection_count=3)
    assert exact_a.coordinate_count == projection.coordinate_count
    assert exact_a.exact_delta_sha256 == exact_b.exact_delta_sha256
    assert projection.project(exact_a.exact_delta) == projection.project(exact_b.exact_delta)
    assert exact_a.profile_max_probability_difference <= 1e-15


def test_fail_closed_profile_and_projection_inputs() -> None:
    game = HUTwoRoundJokerSubgame()
    with pytest.raises(ValueError):
        frozen_regret_table(game, "unknown")
    with pytest.raises(ValueError):
        ProjectionMap(game, projection_count=0)
