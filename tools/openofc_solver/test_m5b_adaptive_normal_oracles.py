from __future__ import annotations

import math

import pytest

from fantasy_fantasy_payoff import continuation_fingerprint
from hu_continuation import (
    HUContinuationState,
    KERNEL_NORMAL_NORMAL,
    zero_continuation_values,
)
from m5a_normal_fantasy_oracle import NormalFantasyFixedPolicyOracle
from m5a_normal_normal_oracle import NormalNormalFixedPolicyOracle
from m5b_adaptive_normal_oracles import (
    AUTHORITY_NF,
    AUTHORITY_NN,
    AdaptiveNormalConfig,
    AdaptiveNormalFantasyOracle,
    AdaptiveNormalNormalOracle,
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
    AUTHORITY as M5I_AUTHORITY,
    HeldoutSeedSpec,
    NormalNormalScreeningConfig,
    screen_normal_normal_candidate,
)


CANDIDATE_IMPL_SHA = "a" * 64
SCREEN_IMPL_SHA = "b" * 64
SCREEN_VALIDATION_SHA = "c" * 64


def tiny_config() -> AdaptiveNormalConfig:
    return AdaptiveNormalConfig(
        training_iterations=1,
        evaluation_samples=2,
        replay_capacity=128,
        fit_epochs=1,
        model_buckets=8,
        learning_rate=0.05,
        l2=0.0,
        huber_delta=1.0,
        epsilon=0.6,
        base_seed=987654,
    )


class _ConstantTerminalEvaluator:
    authority = "M5B_TEST_CONSTANT_TERMINAL"

    def __init__(self, value: float = 1.5) -> None:
        self.value = float(value)

    def evaluate(self, state, continuation_values):
        result = type("ConstantTerminalResult", (), {})()
        result.utility_for_normal = self.value
        return result


def test_normal_normal_materialization_exposes_exact_frozen_m5a_candidate() -> None:
    values = zero_continuation_values()
    state = HUContinuationState(0, 0, 0)
    adaptive = AdaptiveNormalNormalOracle(tiny_config())
    materialized = adaptive.materialize_fixed_policy(state, values)

    assert isinstance(materialized.fixed_oracle, NormalNormalFixedPolicyOracle)
    assert materialized.report.state == state.as_key()
    assert materialized.report.kernel_kind == KERNEL_NORMAL_NORMAL
    assert materialized.report.authority == AUTHORITY_NN
    assert materialized.report.fixed_oracle_id == materialized.fixed_oracle.oracle_id
    assert materialized.report.policy_snapshot_sha256 == materialized.fixed_oracle.snapshot.sha256
    assert materialized.report.training_iterations == tiny_config().training_iterations
    assert materialized.report.solver_infosets > 0
    assert materialized.report.distilled_nodes > 0
    assert materialized.report.action_examples > 0
    assert len(materialized.report.training_seed_ids) == 3
    assert len(set(materialized.report.training_seed_ids)) == 3

    _checked, continuation_sha = continuation_fingerprint(values)
    assert materialized.report.continuation_sha256 == continuation_sha
    assert materialized.fixed_oracle.snapshot.training_continuation_sha256 == continuation_sha


def test_normal_normal_materialization_is_deterministic_for_same_config_state_v() -> None:
    values = zero_continuation_values()
    state = HUContinuationState(1, 0, 0)
    first = AdaptiveNormalNormalOracle(tiny_config()).materialize_fixed_policy(
        state, values
    )
    second = AdaptiveNormalNormalOracle(tiny_config()).materialize_fixed_policy(
        state, values
    )

    assert first.report.sha256 == second.report.sha256
    assert first.fixed_oracle.oracle_id == second.fixed_oracle.oracle_id
    assert first.fixed_oracle.snapshot.sha256 == second.fixed_oracle.snapshot.sha256
    assert first.fixed_oracle.model.payload() == second.fixed_oracle.model.payload()


def test_adaptive_evaluate_matches_the_materialized_candidate_value_path() -> None:
    values = zero_continuation_values()
    state = HUContinuationState(0, 0, 0)
    adaptive = AdaptiveNormalNormalOracle(tiny_config())
    materialized = adaptive.materialize_fixed_policy(state, values)
    direct = materialized.fixed_oracle.evaluate(state, values)
    adaptive_value = adaptive.evaluate(state, values)

    assert adaptive_value.p0_value == direct.p0_value
    assert adaptive_value.standard_error == direct.standard_error
    assert adaptive_value.samples == direct.samples
    assert adaptive_value.continuation_sha256 == direct.continuation_sha256
    assert adaptive_value.oracle_id == adaptive.oracle_id
    assert adaptive.last_report is not None
    assert adaptive.last_materialization is not None
    assert adaptive.last_report.policy_snapshot_sha256 == adaptive.last_materialization.report.policy_snapshot_sha256


def test_materialization_is_bound_to_current_continuation_vector() -> None:
    state = HUContinuationState(0, 0, 0)
    base_values = zero_continuation_values()
    changed_values = dict(base_values)
    changed_values[HUContinuationState(1, 0, 0)] = 0.25

    base = AdaptiveNormalNormalOracle(tiny_config()).materialize_fixed_policy(
        state, base_values
    )
    changed = AdaptiveNormalNormalOracle(tiny_config()).materialize_fixed_policy(
        state, changed_values
    )

    assert base.report.continuation_sha256 != changed.report.continuation_sha256
    assert base.fixed_oracle.snapshot.training_continuation_sha256 != changed.fixed_oracle.snapshot.training_continuation_sha256
    assert base.report.sha256 != changed.report.sha256


def test_wrong_kernel_fails_before_materialization() -> None:
    with pytest.raises(ValueError, match="wrong kernel"):
        AdaptiveNormalNormalOracle(tiny_config()).materialize_fixed_policy(
            HUContinuationState(0, 0, 14), zero_continuation_values()
        )


def test_normal_fantasy_materialization_exposes_frozen_candidate_without_promotion() -> None:
    values = zero_continuation_values()
    state = HUContinuationState(1, 0, 14)
    adaptive = AdaptiveNormalFantasyOracle(
        tiny_config(),
        terminal_evaluator=_ConstantTerminalEvaluator(),
        terminal_evaluator_id="M5B_TEST_CONSTANT_TERMINAL",
    )
    materialized = adaptive.materialize_fixed_policy(state, values)

    assert isinstance(materialized.fixed_oracle, NormalFantasyFixedPolicyOracle)
    assert materialized.report.state == state.as_key()
    assert materialized.report.authority == AUTHORITY_NF
    assert materialized.report.fixed_oracle_id == materialized.fixed_oracle.oracle_id
    assert materialized.report.solver_infosets > 0
    assert materialized.report.action_examples > 0
    value = materialized.fixed_oracle.evaluate(state, values)
    assert math.isfinite(value.p0_value)
    assert value.p0_value == 1.5


def _screening_manifest():
    return freeze_reference_evaluator_manifest(
        evaluator_id="m5i-m5b-integration-screen",
        implementation_sha256=SCREEN_IMPL_SHA,
        validation_evidence_sha256=SCREEN_VALIDATION_SHA,
        method_class=METHOD_LEARNED_RESPONSE_LOWER_BOUND,
        capability=CAPABILITY_SCREENING_ONLY,
        validated_kernel_kinds=(KERNEL_NORMAL_NORMAL,),
        reference_authority=M5I_AUTHORITY,
        validation_provenance="M5B->M5I integration fixture: screening mechanics only",
    )


def _permissive_thresholds():
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
        provenance="M5B-M5I TEST ONLY permissive thresholds",
    )


def test_m5b_candidate_flows_through_m5i_m5h_and_remains_blocked_in_m5c() -> None:
    values = zero_continuation_values()
    state = HUContinuationState(0, 0, 0)
    materialized = AdaptiveNormalNormalOracle(tiny_config()).materialize_fixed_policy(
        state, values
    )
    screen = screen_normal_normal_candidate(
        materialized.fixed_oracle,
        state,
        values,
        (
            HeldoutSeedSpec("m5b-heldout-a", 10101),
            HeldoutSeedSpec("m5b-heldout-b", 20202),
        ),
        NormalNormalScreeningConfig(
            response_training_iterations=1,
            heldout_samples_per_seed=1,
            epsilon=0.6,
            base_seed=30303,
        ),
        provenance=f"screen exact materialization {materialized.report.sha256}",
    )
    response_training_ids = tuple(
        row.training_seed_id for row in screen.response_training
    )
    training_ids = materialized.report.training_seed_ids + response_training_ids
    bundle = collect_normal_route_evidence(
        materialized.fixed_oracle,
        state,
        values,
        screen.seed_metrics,
        implementation_sha256=CANDIDATE_IMPL_SHA,
        reference_evaluator=_screening_manifest(),
        training_seed_ids=training_ids,
        provenance=(
            f"M5B materialization={materialized.report.sha256} "
            f"M5I screen={screen.sha256}"
        ),
        evidence_kind=EVIDENCE_SCREENING,
    )

    cert = certify_route(bundle.route_evidence, _permissive_thresholds())
    assert cert.status == STATUS_BLOCKED
    assert not cert.ready_for_real_bellman
    assert "EVIDENCE_SCREENING_LOWER_BOUND_NOT_CERTIFYING" in cert.failures
