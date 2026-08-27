from __future__ import annotations

from deepofc.hu_two_round_hidden_discard import HUTwoRoundHiddenDiscardSubgame
from deepofc.hu_two_round_joker import HUTwoRoundJokerSubgame
from m5q_freedman_union_feasibility import (
    AUTHORITY,
    evaluate_family,
    family_structure,
    freedman_coordinate_radius,
    report_payload,
    required_iterations_for_concentration_contribution,
    zero_sampled_positive_regret_contribution,
)


def test_exact_family_structures_and_utility_envelopes() -> None:
    joker = family_structure("joker", HUTwoRoundJokerSubgame())
    hidden = family_structure("hidden-discard", HUTwoRoundHiddenDiscardSubgame())

    assert joker.player0_infosets == 4892
    assert joker.player1_infosets == 4892
    assert joker.total_infosets == 9784
    assert joker.action_coordinates == 39456
    assert joker.utility_range == 4.0
    assert joker.sampled_regret_abs_envelope == 4.0
    assert joker.martingale_difference_upper_envelope == 8.0
    assert joker.per_iteration_variance_upper_bound == 16.0

    assert hidden.player0_infosets == 33252
    assert hidden.player1_infosets == 33252
    assert hidden.total_infosets == 66504
    assert hidden.action_coordinates > hidden.total_infosets
    assert hidden.utility_range == 12.0
    assert hidden.sampled_regret_abs_envelope == 12.0
    assert hidden.martingale_difference_upper_envelope == 24.0
    assert hidden.per_iteration_variance_upper_bound == 144.0


def test_normalized_freedman_penalty_decreases_with_iterations() -> None:
    kwargs = {
        "familywise_failure_probability": 0.05,
        "action_coordinates": 39456,
        "martingale_difference_upper_envelope": 8.0,
        "per_iteration_variance_upper_bound": 16.0,
    }
    r1 = freedman_coordinate_radius(iterations=10_000, **kwargs) / 10_000.0
    r2 = freedman_coordinate_radius(iterations=100_000, **kwargs) / 100_000.0
    r3 = freedman_coordinate_radius(iterations=1_000_000, **kwargs) / 1_000_000.0
    assert r3 < r2 < r1


def test_required_iteration_search_is_minimal_and_monotone() -> None:
    structure = family_structure("joker", HUTwoRoundJokerSubgame())
    loose = required_iterations_for_concentration_contribution(
        structure,
        target_exploitability=0.30,
        familywise_failure_probability=0.05,
    )
    strict = required_iterations_for_concentration_contribution(
        structure,
        target_exploitability=0.15,
        familywise_failure_probability=0.05,
    )
    assert strict > loose > 0
    assert zero_sampled_positive_regret_contribution(
        structure,
        iterations=strict,
        familywise_failure_probability=0.05,
    ) <= 0.15
    if strict > 1:
        assert zero_sampled_positive_regret_contribution(
            structure,
            iterations=strict - 1,
            familywise_failure_probability=0.05,
        ) > 0.15


def test_family_result_and_report_remain_non_certifying() -> None:
    result = evaluate_family(
        "joker",
        HUTwoRoundJokerSubgame(),
        target_exploitability=0.15,
        familywise_failure_probability=0.05,
        probe_iterations=1_000_000,
    )
    assert result.coordinate_radius_at_probe > 0.0
    assert result.concentration_only_exploitability_at_probe > 0.0
    assert result.required_iterations_for_target_concentration_only > 1_000_000

    payload = report_payload((result,))
    assert payload["authority"] == AUTHORITY
    assert payload["sampled_positive_regret_term_assumed_zero_for_feasibility"] is True
    assert payload["production_certification_eligible"] is False
    assert payload["real_routes_certified"] == 0
    assert payload["sha256"]
