from __future__ import annotations

import pytest

from hu_continuation import HUContinuationState, KERNEL_NORMAL_FANTASY, zero_continuation_values
from m5a_normal_fantasy_oracle import NormalFantasyFixedPolicyOracle, freeze_policy_snapshot
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
from m5k_normal_fantasy_screening import (
    AUTHORITY,
    HeldoutSeedSpec,
    NormalFantasyScreeningConfig,
    _normal_gain_from_p0,
    screen_normal_fantasy_candidate,
)
from strategic_advantage_model import SparseActionAdvantageModel


class _ConstantTerminalEvaluator:
    authority = "M5K_TEST_CONSTANT_TERMINAL"

    def __init__(self, value: float = 2.0) -> None:
        self.value = float(value)

    def evaluate(self, state, continuation_values):
        result = type("ConstantTerminalResult", (), {})()
        result.utility_for_normal = self.value
        return result


def _frozen(values):
    model = SparseActionAdvantageModel(buckets=1 << 8)
    snapshot = freeze_policy_snapshot(
        model,
        training_continuation_values=values,
        provenance="m5k-unit-fixture",
    )
    return NormalFantasyFixedPolicyOracle(
        model,
        snapshot,
        samples=2,
        base_seed=77,
        terminal_evaluator=_ConstantTerminalEvaluator(),
    )


def _seeds():
    return (
        HeldoutSeedSpec("m5k-heldout-a", 101),
        HeldoutSeedSpec("m5k-heldout-b", 202),
    )


def _config():
    return NormalFantasyScreeningConfig(
        heldout_samples_per_seed=2,
        base_seed=303,
    )


def test_persistent_normal_gain_sign() -> None:
    assert _normal_gain_from_p0(0, 1.0, 1.75) == 0.75
    assert _normal_gain_from_p0(0, 1.75, 1.0) == 0.0
    assert _normal_gain_from_p0(1, -1.0, -1.75) == 0.75
    assert _normal_gain_from_p0(1, -1.75, -1.0) == 0.0
    with pytest.raises(ValueError):
        _normal_gain_from_p0(2, 0.0, 0.0)


def test_identical_policies_have_zero_screening_gain_for_both_normal_orientations() -> None:
    values = zero_continuation_values()
    terminal = _ConstantTerminalEvaluator()
    for state in (
        HUContinuationState(0, 0, 14),
        HUContinuationState(1, 14, 0),
    ):
        candidate = _frozen(values)
        challenger = _frozen(values)
        report = screen_normal_fantasy_candidate(
            candidate,
            challenger,
            state,
            values,
            _seeds(),
            _config(),
            terminal_evaluator=terminal,
            terminal_evaluator_id=terminal.authority,
            provenance="M5K identical-policy unit fixture",
        )
        assert report.authority == AUTHORITY
        assert report.certification_eligible is False
        assert report.max_observed_deviation_gain == 0.0
        assert len(report.seed_metrics) == 2
        for metric in report.seed_metrics:
            if report.normal_player == 0:
                assert metric.p0_deviation_gain == 0.0
                assert metric.p1_deviation_gain is None
            else:
                assert metric.p1_deviation_gain == 0.0
                assert metric.p0_deviation_gain is None


def test_screening_rejects_stale_candidate_or_challenger_vector() -> None:
    values = zero_continuation_values()
    changed = dict(values)
    changed[HUContinuationState(1, 0, 0)] = 0.25
    terminal = _ConstantTerminalEvaluator()
    state = HUContinuationState(0, 0, 14)

    with pytest.raises(ValueError, match="candidate snapshot is stale"):
        screen_normal_fantasy_candidate(
            _frozen(values),
            _frozen(changed),
            state,
            changed,
            _seeds(),
            _config(),
            terminal_evaluator=terminal,
            terminal_evaluator_id=terminal.authority,
            provenance="stale candidate fixture",
        )

    with pytest.raises(ValueError, match="challenger snapshot is stale"):
        screen_normal_fantasy_candidate(
            _frozen(changed),
            _frozen(values),
            state,
            changed,
            _seeds(),
            _config(),
            terminal_evaluator=terminal,
            terminal_evaluator_id=terminal.authority,
            provenance="stale challenger fixture",
        )


def test_wrong_kernel_and_duplicate_heldout_ids_fail_closed() -> None:
    values = zero_continuation_values()
    candidate = _frozen(values)
    terminal = _ConstantTerminalEvaluator()
    with pytest.raises(ValueError, match="Normal/Fantasy"):
        screen_normal_fantasy_candidate(
            candidate,
            candidate,
            HUContinuationState(0, 0, 0),
            values,
            _seeds(),
            _config(),
            terminal_evaluator=terminal,
            terminal_evaluator_id=terminal.authority,
            provenance="wrong kernel fixture",
        )
    with pytest.raises(ValueError, match="unique"):
        screen_normal_fantasy_candidate(
            candidate,
            candidate,
            HUContinuationState(0, 0, 14),
            values,
            (
                HeldoutSeedSpec("dup", 1),
                HeldoutSeedSpec("dup", 2),
            ),
            _config(),
            terminal_evaluator=terminal,
            terminal_evaluator_id=terminal.authority,
            provenance="duplicate fixture",
        )


def _manifest():
    return freeze_reference_evaluator_manifest(
        evaluator_id="m5k-screening-unit",
        implementation_sha256="a" * 64,
        validation_evidence_sha256="b" * 64,
        method_class=METHOD_LEARNED_RESPONSE_LOWER_BOUND,
        capability=CAPABILITY_SCREENING_ONLY,
        validated_kernel_kinds=(KERNEL_NORMAL_FANTASY,),
        reference_authority=AUTHORITY,
        validation_provenance="M5K unit screening only",
    )


def _thresholds():
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
        provenance="M5K TEST ONLY permissive thresholds",
    )


def test_m5k_metrics_flow_through_m5h_but_m5c_refuses_promotion() -> None:
    values = zero_continuation_values()
    state = HUContinuationState(0, 0, 14)
    candidate = _frozen(values)
    terminal = _ConstantTerminalEvaluator()
    screen = screen_normal_fantasy_candidate(
        candidate,
        _frozen(values),
        state,
        values,
        _seeds(),
        _config(),
        terminal_evaluator=terminal,
        terminal_evaluator_id=terminal.authority,
        provenance="M5K->M5H integration fixture",
    )
    bundle = collect_normal_route_evidence(
        candidate,
        state,
        values,
        screen.seed_metrics,
        implementation_sha256="c" * 64,
        reference_evaluator=_manifest(),
        training_seed_ids=("candidate-training", "challenger-training"),
        provenance=f"M5K screen={screen.sha256}",
        evidence_kind=EVIDENCE_SCREENING,
    )
    cert = certify_route(bundle.route_evidence, _thresholds())
    assert cert.status == STATUS_BLOCKED
    assert not cert.ready_for_real_bellman
    assert "EVIDENCE_SCREENING_LOWER_BOUND_NOT_CERTIFYING" in cert.failures
