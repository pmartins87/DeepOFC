from __future__ import annotations

from deepofc.hu_two_round_hidden_discard import HUTwoRoundHiddenDiscardSubgame
from deepofc.hu_two_round_joker import HUTwoRoundJokerSubgame
from deepofc.hu_two_round_mccfr import TwoRoundExternalSamplingMCCFR
from m5q_external_sampling_unbiasedness import frozen_regret_table
from m5q_predictable_visit_variance import (
    AUTHORITY,
    external_sampling_infoset_visit_probabilities,
    predictable_visit_variance_summary,
)


def _hash_mixed_profile(game):
    solver = TwoRoundExternalSamplingMCCFR(game, seed=1)
    solver.regrets = frozen_regret_table(game, "hash-mixed")
    return solver.current_profile()


def _assert_visit_invariants(game, profile, utility_range: float) -> None:
    for traverser in (0, 1):
        visits = external_sampling_infoset_visit_probabilities(game, profile, traverser)
        assert visits
        assert all(0.0 <= probability <= 1.0 for probability in visits.values())
        summary = predictable_visit_variance_summary(
            game,
            profile,
            traverser,
            utility_range=utility_range,
        )
        assert abs(summary.round3_visit_mass - 1.0) <= 1e-10
        assert abs(summary.round4_visit_mass - summary.expected_round4_visit_mass) <= 1e-10
        assert 0.0 < summary.minimum_positive_visit_probability <= summary.maximum_visit_probability <= 1.0
        assert summary.maximum_coordinate_conditional_second_moment_bound <= utility_range * utility_range
        assert summary.total_coordinate_conditional_second_moment_bound > 0.0
        assert summary.authority == AUTHORITY
        assert summary.production_certification_eligible is False
        assert summary.real_routes_certified == 0


def test_joker_uniform_and_hash_mixed_visit_mass_conservation() -> None:
    game = HUTwoRoundJokerSubgame()
    _assert_visit_invariants(game, game.uniform_profile(), 4.0)
    _assert_visit_invariants(game, _hash_mixed_profile(game), 4.0)


def test_hidden_discard_uniform_visit_mass_conservation() -> None:
    game = HUTwoRoundHiddenDiscardSubgame()
    _assert_visit_invariants(game, game.uniform_profile(), 12.0)
