from __future__ import annotations

from m5q_certification_architecture_decision import (
    AUTHORITY,
    frozen_m5q_architecture_decision,
)


def test_decision_binds_required_m5q_evidence() -> None:
    report = frozen_m5q_architecture_decision()
    by_id = {row.gate_id: row for row in report.evidence}
    assert by_id["M5Q_EXPLORATION_SUPPORT_FEASIBILITY"].workflow_run_id == 33117273274
    assert by_id["M5Q_ADAPTIVE_PREDICTABLE_FREEDMAN_TRAJECTORY"].workflow_run_id == 33125700677
    assert len(report.evidence) == 7
    assert all(len(row.payload_sha256) == 64 for row in report.evidence)


def test_exploration_route_is_deprioritized_even_at_best_support_endpoint() -> None:
    report = frozen_m5q_architecture_decision()
    assert report.exploration_epsilon1_joker_floor > 0.0
    assert report.exploration_epsilon1_hidden_floor > 0.0
    assert report.exploration_epsilon1_joker_required_iterations == 918799060363021
    assert report.exploration_epsilon1_hidden_required_iterations == 1382605782910640640
    assert report.global_floor_exploration_status == "DEPRIORITIZED_AS_PRIMARY_PRODUCTION_CERTIFICATE"


def test_actual_predictable_freedman_gap_is_bound_and_large() -> None:
    report = frozen_m5q_architecture_decision()
    assert report.adaptive_checkpoint_iterations == 64
    assert report.adaptive_concentration_additive == 5592.373477969387
    assert report.adaptive_exact_exploitability == 0.6407294367903822
    assert report.adaptive_concentration_to_exact_ratio > 8700.0
    assert report.scalar_coordinate_freedman_status == "DEPRIORITIZED_AS_PRIMARY_PRODUCTION_CERTIFICATE"


def test_decision_fails_closed_and_does_not_overclaim() -> None:
    report = frozen_m5q_architecture_decision()
    assert report.authority == AUTHORITY
    assert report.preferred_next_architecture == "FROZEN_POLICY_INDEPENDENT_DEVIATION_BEST_RESPONSE_CERTIFICATION"
    assert report.support_free_methods_globally_rejected is False
    assert report.production_solver_modified is False
    assert report.production_certification_eligible is False
    assert report.real_routes_certified == 0
    assert len(report.sha256) == 64
    payload = report.payload()
    assert payload["sha256"] == report.sha256
    assert payload["decision"]["support_free_methods_globally_rejected"] is False
