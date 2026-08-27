from __future__ import annotations

from deepofc.hu_two_round_hidden_discard import HUTwoRoundHiddenDiscardSubgame
from deepofc.hu_two_round_joker import HUTwoRoundJokerSubgame
from m5q_support_free_martingale_prerequisites import (
    AUTHORITY,
    M5Q_A_UNBIASEDNESS_PAYLOAD_SHA256,
    audit_support_free_prerequisites,
    sampled_regret_path_has_explicit_division,
)


def _report():
    return audit_support_free_prerequisites(
        (
            ("joker", HUTwoRoundJokerSubgame()),
            ("hidden-discard", HUTwoRoundHiddenDiscardSubgame()),
        )
    )


def test_current_sampled_regret_path_has_no_explicit_division() -> None:
    assert sampled_regret_path_has_explicit_division() is False


def test_exact_reduced_utility_ranges_bound_coordinate_increment() -> None:
    report = _report()
    by_id = {row.family_id: row for row in report.families}
    assert by_id["joker"].minimum_terminal_utility == -2.0
    assert by_id["joker"].maximum_terminal_utility == 2.0
    assert by_id["joker"].sampled_regret_coordinate_abs_envelope == 4.0
    assert by_id["hidden-discard"].minimum_terminal_utility == -6.0
    assert by_id["hidden-discard"].maximum_terminal_utility == 6.0
    assert by_id["hidden-discard"].sampled_regret_coordinate_abs_envelope == 12.0
    assert report.bounded_increment_prerequisite_pass is True


def test_unbiasedness_binding_remains_diagnostic_only() -> None:
    report = _report()
    assert report.m5q_a_unbiasedness_payload_sha256 == M5Q_A_UNBIASEDNESS_PAYLOAD_SHA256
    assert report.unbiasedness_binding_status == "FINITE_MONTE_CARLO_DIAGNOSTIC_NOT_PROOF"


def test_current_solver_fails_closed_on_missing_theorem_average() -> None:
    report = _report()
    assert "behavioral_time_average_profile" in report.available_average_profile_methods
    assert report.theorem_compatible_reach_weighted_average_available is False
    assert report.support_free_certificate_prerequisites_complete is False
    assert report.next_blocker == "THEOREM_COMPATIBLE_REACH_WEIGHTED_AVERAGE_MISSING"


def test_no_predictable_variance_accounting_is_invented() -> None:
    report = _report()
    assert report.predictable_variance_accounting_available is False
    assert report.production_certification_eligible is False
    assert report.real_routes_certified == 0
    assert report.authority == AUTHORITY
    assert report.sha256
