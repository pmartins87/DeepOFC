from __future__ import annotations

import math

import pytest

from hu_continuation import (
    HUContinuationState,
    KERNEL_NORMAL_NORMAL,
    zero_continuation_values,
)
from m5a_normal_normal_oracle import (
    NormalNormalFixedPolicyOracle,
    freeze_policy_snapshot,
)
from m5c_route_certification import (
    EVIDENCE_SCREENING,
    STATUS_BLOCKED,
    KernelThresholds,
    certify_route,
    freeze_threshold_manifest,
)
from m5h_normal_heldout_evidence import collect_normal_route_evidence
from m5h_reference_evaluator_manifest import (
    CAPABILITY_SCREENING_ONLY,
    METHOD_LEARNED_RESPONSE_LOWER_BOUND,
    freeze_reference_evaluator_manifest,
)
from m5i_normal_normal_screening import (
    AUTHORITY,
    HeldoutSeedSpec,
    NormalNormalScreeningConfig,
    screen_normal_normal_candidate,
)
from strategic_advantage_model import SparseActionAdvantageModel


CANDIDATE_IMPL_SHA = "a" * 64
SCREEN_IMPL_SHA = "b" * 64
SCREEN_VALIDATION_SHA = "c" * 64


def candidate() -> NormalNormalFixedPolicyOracle:
    values = zero_continuation_values()
    model = SparseActionAdvantageModel(buckets=8, seed=77)
    snapshot = freeze_policy_snapshot(
        model,
        training_continuation_values=values,
        provenance="M5I deterministic zero-model unit candidate",
    )
    return NormalNormalFixedPolicyOracle(
        model,
        snapshot,
        samples=2,
        base_seed=123,
    )


def tiny_config() -> NormalNormalScreeningConfig:
    return NormalNormalScreeningConfig(
        response_training_iterations=2,
        heldout_samples_per_seed=2,
        epsilon=0.6,
        base_seed=456,
    )


def heldout_seeds() -> tuple[HeldoutSeedSpec, ...]:
    return (
        HeldoutSeedSpec("heldout-2", 222),
        HeldoutSeedSpec("heldout-1", 111),
    )


def run_state(button: int):
    return screen_normal_normal_candidate(
        candidate(),
        HUContinuationState(button, 0, 0),
        zero_continuation_values(),
        heldout_seeds(),
        tiny_config(),
        provenance=f"M5I unit screening button={button}",
    )


def screening_manifest():
    return freeze_reference_evaluator_manifest(
        evaluator_id="m5i-normal-normal-learned-response-screen",
        implementation_sha256=SCREEN_IMPL_SHA,
        validation_evidence_sha256=SCREEN_VALIDATION_SHA,
        method_class=METHOD_LEARNED_RESPONSE_LOWER_BOUND,
        capability=CAPABILITY_SCREENING_ONLY,
        validated_kernel_kinds=(KERNEL_NORMAL_NORMAL,),
        reference_authority=AUTHORITY,
        validation_provenance="M5I unit validation: lower-bound screening mechanics only",
    )


def permissive_test_thresholds():
    huge = KernelThresholds(
        min_heldout_seeds=2,
        min_heldout_samples=1,
        max_value_standard_error=1e9,
        max_unilateral_deviation=1e9,
    )
    return freeze_threshold_manifest(
        normal_normal=huge,
        normal_fantasy=huge,
        fantasy_fantasy=KernelThresholds(
            min_heldout_seeds=2,
            min_heldout_samples=1,
            max_value_standard_error=1e9,
            max_unilateral_deviation=1e9,
            max_support_gap=1e9,
            max_model_q_error=1e9,
        ),
        provenance="M5I TEST ONLY deliberately permissive thresholds",
    )


def test_both_normal_normal_continuation_states_run() -> None:
    for button in (0, 1):
        report = run_state(button)
        assert report.state == HUContinuationState(button, 0, 0).as_key()
        assert report.authority == AUTHORITY
        assert not report.certification_eligible
        assert report.heldout_seed_ids == ("heldout-1", "heldout-2")
        assert len(report.response_training) == 2
        assert {row.persistent_player for row in report.response_training} == {0, 1}
        assert len(report.seed_metrics) == 2
        assert math.isfinite(report.max_p0_deviation_gain)
        assert math.isfinite(report.max_p1_deviation_gain)
        assert report.max_p0_deviation_gain >= 0.0
        assert report.max_p1_deviation_gain >= 0.0
        assert report.max_observed_deviation_gain == max(
            report.max_p0_deviation_gain,
            report.max_p1_deviation_gain,
        )


def test_report_identity_is_deterministic_and_seed_order_independent() -> None:
    state = HUContinuationState(0, 0, 0)
    first = screen_normal_normal_candidate(
        candidate(),
        state,
        zero_continuation_values(),
        heldout_seeds(),
        tiny_config(),
        provenance="deterministic fixture",
    )
    second = screen_normal_normal_candidate(
        candidate(),
        state,
        zero_continuation_values(),
        tuple(reversed(heldout_seeds())),
        tiny_config(),
        provenance="deterministic fixture",
    )
    assert first.sha256 == second.sha256
    assert first.seed_metrics == second.seed_metrics
    assert first.response_training == second.response_training


def test_requires_two_unique_heldout_seeds() -> None:
    with pytest.raises(ValueError, match="at least two"):
        screen_normal_normal_candidate(
            candidate(),
            HUContinuationState(0, 0, 0),
            zero_continuation_values(),
            (HeldoutSeedSpec("one", 1),),
            tiny_config(),
            provenance="too few seeds",
        )

    with pytest.raises(ValueError, match="unique"):
        screen_normal_normal_candidate(
            candidate(),
            HUContinuationState(0, 0, 0),
            zero_continuation_values(),
            (HeldoutSeedSpec("dup", 1), HeldoutSeedSpec("dup", 2)),
            tiny_config(),
            provenance="duplicate seed ids",
        )


def test_wrong_kernel_is_rejected() -> None:
    with pytest.raises(ValueError, match="Normal/Normal"):
        screen_normal_normal_candidate(
            candidate(),
            HUContinuationState(0, 0, 14),
            zero_continuation_values(),
            heldout_seeds(),
            tiny_config(),
            provenance="wrong kernel",
        )


def test_m5i_to_m5h_to_m5c_remains_screening_only() -> None:
    state = HUContinuationState(0, 0, 0)
    frozen_candidate = candidate()
    report = screen_normal_normal_candidate(
        frozen_candidate,
        state,
        zero_continuation_values(),
        heldout_seeds(),
        tiny_config(),
        provenance="M5I->M5H integration fixture",
    )
    training_ids = tuple(row.training_seed_id for row in report.response_training)
    bundle = collect_normal_route_evidence(
        frozen_candidate,
        state,
        zero_continuation_values(),
        report.seed_metrics,
        implementation_sha256=CANDIDATE_IMPL_SHA,
        reference_evaluator=screening_manifest(),
        training_seed_ids=training_ids,
        provenance=f"M5I screening report {report.sha256}",
        evidence_kind=EVIDENCE_SCREENING,
    )
    assert bundle.route_evidence.evidence_kind == EVIDENCE_SCREENING
    assert bundle.report.reference_evaluator_manifest_sha256 == screening_manifest().sha256

    cert = certify_route(bundle.route_evidence, permissive_test_thresholds())
    assert cert.status == STATUS_BLOCKED
    assert not cert.ready_for_real_bellman
    assert "EVIDENCE_SCREENING_LOWER_BOUND_NOT_CERTIFYING" in cert.failures
