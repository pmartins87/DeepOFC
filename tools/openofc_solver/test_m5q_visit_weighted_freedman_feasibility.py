from __future__ import annotations

from deepofc.hu_two_round_joker import HUTwoRoundJokerSubgame
from m5q_visit_weighted_freedman_feasibility import (
    AUTHORITY,
    concentration_only_from_visits,
    evaluate_profile,
    required_iterations_from_visits,
)


def test_concentration_floor_decreases_with_iterations() -> None:
    visits = (0.25, 0.1, 0.01, 0.0)
    kwargs = {
        "utility_range": 4.0,
        "familywise_failure_probability": 0.05,
        "action_coordinates": 100,
    }
    v1 = concentration_only_from_visits(visits, iterations=10_000, **kwargs)
    v2 = concentration_only_from_visits(visits, iterations=100_000, **kwargs)
    v3 = concentration_only_from_visits(visits, iterations=1_000_000, **kwargs)
    assert v3 < v2 < v1


def test_required_iteration_search_is_minimal() -> None:
    visits = (0.25, 0.1, 0.01, 0.0)
    kwargs = {
        "utility_range": 4.0,
        "familywise_failure_probability": 0.05,
        "action_coordinates": 100,
    }
    required = required_iterations_from_visits(
        visits,
        target_exploitability=0.15,
        **kwargs,
    )
    assert concentration_only_from_visits(visits, iterations=required, **kwargs) <= 0.15
    if required > 1:
        assert concentration_only_from_visits(visits, iterations=required - 1, **kwargs) > 0.15


def test_joker_uniform_result_is_non_certifying_and_structurally_tighter() -> None:
    game = HUTwoRoundJokerSubgame()
    result = evaluate_profile(
        "joker",
        "uniform",
        game,
        game.uniform_profile(),
        utility_range=4.0,
        familywise_failure_probability=0.05,
        target_exploitability=0.15,
        probe_iterations=1_000_000,
    )
    assert result.infosets == 9784
    assert result.action_coordinates == 39456
    assert 0 < result.positive_visit_infosets <= result.infosets
    assert 0.0 < result.minimum_positive_visit_probability <= result.maximum_visit_probability <= 1.0
    assert result.concentration_only_exploitability_at_probe < 102.15144671638896
    assert result.required_iterations_for_target_concentration_only < 462168059358
    assert result.authority == AUTHORITY
    assert result.production_certification_eligible is False
    assert result.real_routes_certified == 0
