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
from m5k_normal_fantasy_screening import HeldoutSeedSpec
from m5n_normal_fantasy_paired_screening import (
    AUTHORITY,
    PairedNormalFantasyConfig,
    _signed_normal_gain,
    screen_paired_normal_fantasy_candidate,
)
from strategic_advantage_model import SparseActionAdvantageModel


class _ConstantTerminalEvaluator:
    authority = "M5N_TEST_CONSTANT_TERMINAL"

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
        provenance="m5n-unit-fixture",
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
        HeldoutSeedSpec("m5n-heldout-a", 101),
        HeldoutSeedSpec("m5n-heldout-b", 202),
        HeldoutSeedSpec("m5n-heldout-c", 303),
        HeldoutSeedSpec("m5n-heldout-d", 404),
    )


def _config():
    return PairedNormalFantasyConfig(
        heldout_samples_per_seed=2,
        confidence_multiplier=3.182,
        base_seed=505,
    )


def test_signed_gain_respects_persistent_normal_orientation() -> None:
    assert _signed_normal_gain(0, 1.0, 1.75) == 0.75
    assert _signed_normal_gain(0, 1.75, 1.0) == -0.75
    assert _signed_normal_gain(1, -1.0, -1.75) == 0.75
    assert _signed_normal_gain(1, -1.75, -1.0) == -0.75
    with pytest.raises(ValueError):
        _signed_normal_gain(2, 0.0, 0.0)


def test_identical_policies_have_zero_paired_gain_and_uncertainty() -> None:
    values = zero_continuation_values()
    terminal = _ConstantTerminalEvaluator()
    for state in (
        HUContinuationState(0, 0, 14),
        HUContinuationState(1, 14, 0),
    ):
        report = screen_paired_normal_fantasy_candidate(
            _frozen(values),
            _frozen(values),
            state,
            values,
            _seeds(),
            _config(),
            terminal_evaluator=terminal,
            terminal_evaluator_id=terminal.authority,
            provenance="M5N identical-policy fixture",
        )
        assert report.authority == AUTHORITY
        assert report.certification_eligible is False
        assert report.max_conservative_deviation_signal == 0.0
        assert report.aggregate.seed_mean_signed_gain == 0.0
        assert report.aggregate.seed_standard_error == 0.0
        assert len(report.paired_seed_metrics) == 4
        for metric in report.paired_seed_metrics:
            assert metric.signed_normal_gain == 0.0
            assert metric.gain_standard_error == 0.0
            m5h = metric.as_m5h_diagnostic()
            if report.normal_player == 0:
                assert m5h.p0_deviation_gain == 0.0
                assert m5h.p1_deviation_gain is None
            else:
                assert m5h.p1_deviation_gain == 0.0
                assert m5h.p0_deviation_gain is None


def test_requires_four_unique_heldout_seed_identities() -> None:
    values = zero_continuation_values()
    candidate = _frozen(values)
    terminal = _ConstantTerminalEvaluator()
    state = HUContinuationState(0, 0, 14)
    with pytest.raises(ValueError, match="at least four"):
        screen_paired_normal_fantasy_candidate(
            candidate,
            candidate,
            state,
            values,
            _seeds()[:3],
            _config(),
            terminal_evaluator=terminal,
            terminal_evaluator_id=terminal.authority,
            provenance="too-few-seeds fixture",
        )
    with pytest.raises(ValueError, match="unique"):
        screen_paired_normal_fantasy_candidate(
            candidate,
            candidate,
            state,
            values,
            (
                HeldoutSeedSpec("dup", 1),
                HeldoutSeedSpec("dup", 2),
                HeldoutSeedSpec("c", 3),
                HeldoutSeedSpec("d", 4),
            ),
            _config(),
            terminal_evaluator=terminal,
            terminal_evaluator_id=terminal.authority,
            provenance="duplicate-seeds fixture",
        )


def test_stale_vectors_and_wrong_kernel_fail_closed() -> None:
    values = zero_continuation_values()
    changed = dict(values)
    changed[HUContinuationState(1, 0, 0)] = 0.25
    terminal = _ConstantTerminalEvaluator()
    with pytest.raises(ValueError, match="candidate snapshot is stale"):
        screen_paired_normal_fantasy_candidate(
            _frozen(values),
            _frozen(changed),
            HUContinuationState(0, 0, 14),
            changed,
            _seeds(),
            _config(),
            terminal_evaluator=terminal,
            terminal_evaluator_id=terminal.authority,
            provenance="stale-candidate fixture",
        )
    with pytest.raises(ValueError, match="challenger snapshot is stale"):
        screen_paired_normal_fantasy_candidate(
            _frozen(changed),
            _frozen(values),
            HUContinuationState(0, 0, 14),
            changed,
            _seeds(),
            _config(),
            terminal_evaluator=terminal,
            terminal_evaluator_id=terminal.authority,
            provenance="stale-challenger fixture",
        )
    with pytest.raises(ValueError, match="Normal/Fantasy"):
        screen_paired_normal_fantasy_candidate(
            _frozen(values),
            _frozen(values),
            HUContinuationState(0, 0, 0),
            values,
            _seeds(),
            _config(),
            terminal_evaluator=terminal,
            terminal_evaluator_id=terminal.authority,
            provenance="wrong-kernel fixture",
        )


def _manifest():
    return freeze_reference_evaluator_manifest(
        evaluator_id="m5n-screening-unit",
        implementation_sha256="a" * 64,
        validation_evidence_sha256="b" * 64,
        method_class=METHOD_LEARNED_RESPONSE_LOWER_BOUND,
        capability=CAPABILITY_SCREENING_ONLY,
        validated_kernel_kinds=(KERNEL_NORMAL_FANTASY,),
        reference_authority=AUTHORITY,
        validation_provenance="M5N unit screening only",
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
        provenance="M5N TEST ONLY permissive thresholds",
    )


def test_m5n_metrics_flow_to_m5h_but_cannot_certify() -> None:
    values = zero_continuation_values()
    state = HUContinuationState(0, 0, 14)
    candidate = _frozen(values)
    terminal = _ConstantTerminalEvaluator()
    report = screen_paired_normal_fantasy_candidate(
        candidate,
        _frozen(values),
        state,
        values,
        _seeds(),
        _config(),
        terminal_evaluator=terminal,
        terminal_evaluator_id=terminal.authority,
        provenance="M5N->M5H integration fixture",
    )
    bundle = collect_normal_route_evidence(
        candidate,
        state,
        values,
        tuple(metric.as_m5h_diagnostic() for metric in report.paired_seed_metrics),
        implementation_sha256="c" * 64,
        reference_evaluator=_manifest(),
        training_seed_ids=("candidate-training", "challenger-training"),
        provenance=f"M5N screen={report.sha256}",
        evidence_kind=EVIDENCE_SCREENING,
    )
    cert = certify_route(bundle.route_evidence, _thresholds())
    assert cert.status == STATUS_BLOCKED
    assert not cert.ready_for_real_bellman
    assert "EVIDENCE_SCREENING_LOWER_BOUND_NOT_CERTIFYING" in cert.failures
