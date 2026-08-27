from __future__ import annotations

import math
import pytest

from deepofc.hu_two_round_hidden_discard import HUTwoRoundHiddenDiscardSubgame
from deepofc.hu_two_round_joker import HUTwoRoundJokerSubgame
from m5r_frozen_policy_br_reference import (
    REDUCED_SCOPE,
    REFERENCE_AUTHORITY,
    evaluate_frozen_policy_exact_br,
    freeze_reference_evaluator_manifest,
    frozen_policy_payload,
    validate_exact_reference,
)


@pytest.fixture(scope="module")
def exact_validation():
    joker = HUTwoRoundJokerSubgame()
    hidden = HUTwoRoundHiddenDiscardSubgame()
    return validate_exact_reference(
        (
            ("joker", joker, joker.uniform_profile()),
            ("hidden-discard", hidden, hidden.uniform_profile()),
        )
    )


def test_frozen_policy_identity_is_deterministic_and_probability_sensitive() -> None:
    game = HUTwoRoundJokerSubgame()
    uniform = game.uniform_profile()
    first = min(game.info_actions, key=lambda info: repr(info))
    actions = game.actions(first)
    mutated = {info: dict(dist) for info, dist in uniform.items()}
    mutated[first] = {
        action: 1.0 if action == actions[0] else 0.0
        for action in actions
    }
    left = frozen_policy_payload(game, uniform)
    repeat = frozen_policy_payload(game, uniform)
    right = frozen_policy_payload(game, mutated)
    assert left["sha256"] == repeat["sha256"]
    assert left["sha256"] != right["sha256"]
    assert len(left["infosets"]) == len(game.info_actions)


def test_exact_reference_matches_independent_expected_value_and_known_uniform_values(exact_validation) -> None:
    assert exact_validation.validation_status == "PASS"
    assert exact_validation.validation_scope == REDUCED_SCOPE
    assert exact_validation.maximum_crosscheck_abs_error <= 1e-12
    rows = {row.family_id: row for row in exact_validation.rows}

    joker = rows["joker"]
    assert math.isclose(joker.expected_p0_utility, 0.0, abs_tol=1e-12)
    assert math.isclose(joker.br0_value, 1.125, abs_tol=1e-12)
    assert math.isclose(joker.br1_value, 1.125, abs_tol=1e-12)
    assert math.isclose(joker.nash_conv, 2.25, abs_tol=1e-12)
    assert math.isclose(joker.exploitability, 1.125, abs_tol=1e-12)
    assert joker.br0_infosets + joker.br1_infosets == joker.infosets
    assert joker.authority == REFERENCE_AUTHORITY

    hidden = rows["hidden-discard"]
    assert math.isclose(hidden.expected_p0_utility, 0.0, abs_tol=1e-12)
    assert math.isclose(hidden.br0_value, 2.099206349206348, abs_tol=1e-12)
    assert math.isclose(hidden.br1_value, 2.0992063492063475, abs_tol=1e-12)
    assert math.isclose(hidden.nash_conv, 4.198412698412696, abs_tol=1e-12)
    assert math.isclose(hidden.exploitability, 2.099206349206348, abs_tol=1e-12)
    assert hidden.br0_infosets + hidden.br1_infosets == hidden.infosets

    for row in rows.values():
        assert math.isclose(
            row.nash_conv,
            row.p0_deviation_gain + row.p1_deviation_gain,
            abs_tol=1e-12,
        )
        assert row.production_certification_eligible is False
        assert row.real_routes_certified == 0
        assert len(row.profile_sha256) == 64
        assert len(row.sha256) == 64


def test_reference_manifest_exact_scope_can_be_eligible(exact_validation) -> None:
    manifest = freeze_reference_evaluator_manifest(
        evaluator_id="m5r-exact-two-round-reference-v1",
        implementation_sha256="a" * 64,
        validation_evidence_sha256=exact_validation.sha256,
        validation_status=exact_validation.validation_status,
        validation_scope=exact_validation.validation_scope,
        evaluator_authority=REFERENCE_AUTHORITY,
        guaranteed_missed_deviation_upper_bound=0.0,
        certification_eligible=True,
        provenance="M5R reduced-game exact-BR gate fixture",
    )
    assert manifest.certification_eligible is True
    assert manifest.guaranteed_missed_deviation_upper_bound == 0.0
    assert manifest.validation_scope == REDUCED_SCOPE
    assert manifest.production_route_certification_eligible is False
    assert manifest.real_routes_certified == 0
    assert len(manifest.sha256) == 64


def test_approximate_manifest_without_missed_gain_bound_fails_closed() -> None:
    diagnostic = freeze_reference_evaluator_manifest(
        evaluator_id="approx-screen",
        implementation_sha256="b" * 64,
        validation_evidence_sha256="c" * 64,
        validation_status="DIAGNOSTIC_ONLY",
        validation_scope="REDUCED_SCREENING_ONLY",
        evaluator_authority="APPROX_EXPLOITER_SCREEN_NOT_CERTIFICATION_REFERENCE",
        guaranteed_missed_deviation_upper_bound=None,
        certification_eligible=False,
        provenance="test screening evaluator",
    )
    assert diagnostic.certification_eligible is False
    assert diagnostic.guaranteed_missed_deviation_upper_bound is None

    with pytest.raises(ValueError, match="guaranteed missed-deviation upper bound"):
        freeze_reference_evaluator_manifest(
            evaluator_id="invalid-promoted-approx",
            implementation_sha256="b" * 64,
            validation_evidence_sha256="c" * 64,
            validation_status="PASS",
            validation_scope="REDUCED_SCREENING_ONLY",
            evaluator_authority="APPROX_EXPLOITER_SCREEN_NOT_CERTIFICATION_REFERENCE",
            guaranteed_missed_deviation_upper_bound=None,
            certification_eligible=True,
            provenance="must fail closed",
        )
