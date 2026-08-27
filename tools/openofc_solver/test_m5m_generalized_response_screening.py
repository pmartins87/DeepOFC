from __future__ import annotations

from dataclasses import replace

import pytest

from hu_continuation import HUContinuationState, all_states, zero_continuation_values
from m5b_adaptive_normal_oracles import AdaptiveNormalConfig, AdaptiveNormalNormalOracle
from m5i_normal_normal_screening import HeldoutSeedSpec
from m5m_generalized_response_screening import (
    AUTHORITY,
    GeneralizedResponseConfig,
    _aggregate_gain,
    screen_generalized_normal_normal_candidate,
)


def candidate_config() -> AdaptiveNormalConfig:
    return AdaptiveNormalConfig(
        training_iterations=32,
        evaluation_samples=8,
        replay_capacity=2_000,
        fit_epochs=1,
        model_buckets=1 << 10,
        learning_rate=0.08,
        l2=1e-6,
        huber_delta=1.0,
        epsilon=0.6,
        base_seed=2026083001,
    )


def screen_config() -> GeneralizedResponseConfig:
    return GeneralizedResponseConfig(
        response_training_iterations=32,
        epsilon=0.6,
        replay_capacity=2_000,
        fit_epochs=1,
        model_buckets=1 << 10,
        learning_rate=0.08,
        l2=1e-6,
        huber_delta=1.0,
        heldout_samples_per_seed=2,
        confidence_multiplier=3.182,
        base_seed=2026083017,
    )


def seeds():
    return (
        HeldoutSeedSpec("m5m-test-01", 2026083031),
        HeldoutSeedSpec("m5m-test-02", 2026083047),
        HeldoutSeedSpec("m5m-test-03", 2026083061),
        HeldoutSeedSpec("m5m-test-04", 2026083079),
    )


def materialized_candidate():
    state = HUContinuationState(0, 0, 0)
    values = zero_continuation_values()
    materialized = AdaptiveNormalNormalOracle(candidate_config()).materialize_fixed_policy(
        state, values
    )
    return state, values, materialized.fixed_oracle


def test_aggregate_lower_signal_is_conservative_and_nonnegative() -> None:
    exact = _aggregate_gain(0, (1.0, 1.0, 1.0, 1.0), 3.182)
    assert exact.seed_mean_signed_gain == 1.0
    assert exact.seed_standard_error == 0.0
    assert exact.conservative_lower_signal == 1.0

    noisy = _aggregate_gain(1, (1.0, -1.0, 1.0, -1.0), 3.182)
    assert noisy.seed_mean_signed_gain == 0.0
    assert noisy.seed_standard_error > 0.0
    assert noisy.conservative_lower_signal == 0.0


def test_m5m_materializes_generalized_responses_and_never_certifies() -> None:
    state, values, candidate = materialized_candidate()
    report = screen_generalized_normal_normal_candidate(
        candidate,
        state,
        values,
        seeds(),
        screen_config(),
        provenance="small deterministic M5M unit fixture",
    )
    assert report.authority == AUTHORITY
    assert not report.certification_eligible
    assert report.state == state.as_key()
    assert len(report.response_materializations) == 2
    assert len(report.paired_seed_metrics) == 4
    assert report.max_conservative_deviation_signal >= 0.0
    assert len(report.sha256) == 64

    for response in report.response_materializations:
        assert response.training_iterations == 32
        assert response.tabular_infosets > 0
        assert response.distilled_nodes > 0
        assert response.action_examples > 0
        assert response.validation_nodes > 0
        assert response.validation_actions > 0
        assert len(response.model_sha256) == 64
        assert 0.0 <= response.validation_top1_accuracy <= 1.0

    for row in report.paired_seed_metrics:
        assert row.samples == 2
        assert row.profile_value_standard_error >= 0.0
        assert row.p0_gain_standard_error >= 0.0
        assert row.p1_gain_standard_error >= 0.0


def test_m5m_rejects_stale_continuation_candidate_before_screening() -> None:
    state, values, candidate = materialized_candidate()
    changed = dict(values)
    other = next(item for item in all_states() if item != state)
    changed[other] = 1.0
    with pytest.raises(ValueError, match="stale"):
        screen_generalized_normal_normal_candidate(
            candidate,
            state,
            changed,
            seeds(),
            screen_config(),
            provenance="stale continuation test",
        )


def test_m5m_requires_four_unique_heldout_seed_identities() -> None:
    state, values, candidate = materialized_candidate()
    with pytest.raises(ValueError, match="at least four"):
        screen_generalized_normal_normal_candidate(
            candidate,
            state,
            values,
            seeds()[:3],
            screen_config(),
            provenance="too few seeds",
        )

    duplicate = (
        seeds()[0],
        replace(seeds()[1], seed_id=seeds()[0].seed_id),
        seeds()[2],
        seeds()[3],
    )
    with pytest.raises(ValueError, match="unique"):
        screen_generalized_normal_normal_candidate(
            candidate,
            state,
            values,
            duplicate,
            screen_config(),
            provenance="duplicate seed ids",
        )
