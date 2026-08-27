from __future__ import annotations

import math

import pytest

from hu_continuation import HUContinuationState, zero_continuation_values
from m5c_route_certification import EVIDENCE_HELDOUT, EVIDENCE_TEST
from m5h_normal_heldout_evidence import (
    HeldoutNormalSeedMetric,
    collect_normal_route_evidence,
)


class DummyOracle:
    oracle_id = "m5h-test-oracle"


IMPL_SHA = "a" * 64
EVALUATOR_SHA = "b" * 64


def nn_rows() -> tuple[HeldoutNormalSeedMetric, ...]:
    return (
        HeldoutNormalSeedMetric(
            "heldout-b",
            100,
            3.0,
            p0_deviation_gain=0.20,
            p1_deviation_gain=0.40,
        ),
        HeldoutNormalSeedMetric(
            "heldout-a",
            100,
            1.0,
            p0_deviation_gain=0.30,
            p1_deviation_gain=0.10,
        ),
    )


def collect_nn(*, evidence_kind: str = EVIDENCE_HELDOUT):
    return collect_normal_route_evidence(
        DummyOracle(),
        HUContinuationState(0, 0, 0),
        zero_continuation_values(),
        nn_rows(),
        implementation_sha256=IMPL_SHA,
        reference_evaluator_sha256=EVALUATOR_SHA,
        reference_authority="independent-reference-test",
        training_seed_ids=("train-2", "train-1"),
        provenance="m5h deterministic unit fixture",
        evidence_kind=evidence_kind,
    )


def test_normal_normal_aggregation_is_conservative_and_deterministic() -> None:
    first = collect_nn()
    second = collect_normal_route_evidence(
        DummyOracle(),
        HUContinuationState(0, 0, 0),
        zero_continuation_values(),
        tuple(reversed(nn_rows())),
        implementation_sha256=IMPL_SHA,
        reference_evaluator_sha256=EVALUATOR_SHA,
        reference_authority="independent-reference-test",
        training_seed_ids=("train-1", "train-2"),
        provenance="m5h deterministic unit fixture",
        evidence_kind=EVIDENCE_HELDOUT,
    )

    assert first.report.sha256 == second.report.sha256
    assert first.route_evidence.sha256 == second.route_evidence.sha256
    assert first.report.heldout_seed_ids == ("heldout-a", "heldout-b")
    assert first.report.training_seed_ids == ("train-1", "train-2")
    assert first.report.heldout_samples == 200
    assert first.report.mean_profile_p0_value == 2.0
    assert math.isclose(first.report.value_standard_error, 1.0)
    assert first.report.p0_max_deviation_gain == 0.30
    assert first.report.p1_max_deviation_gain == 0.40
    assert first.report.max_unilateral_deviation == 0.40
    assert first.route_evidence.max_unilateral_deviation == 0.40
    assert first.route_evidence.evidence_kind == EVIDENCE_HELDOUT
    assert first.route_evidence.support_gap is None
    assert first.route_evidence.model_q_error is None


def test_normal_fantasy_requires_only_the_normal_players_deviation() -> None:
    p0_normal = collect_normal_route_evidence(
        DummyOracle(),
        HUContinuationState(0, 0, 14),
        zero_continuation_values(),
        (
            HeldoutNormalSeedMetric("a", 20, 0.5, p0_deviation_gain=0.11),
            HeldoutNormalSeedMetric("b", 20, 0.7, p0_deviation_gain=0.17),
        ),
        implementation_sha256=IMPL_SHA,
        reference_evaluator_sha256=EVALUATOR_SHA,
        reference_authority="one-sided-reference-test",
        training_seed_ids=("train",),
        provenance="p0 normal fixture",
        evidence_kind=EVIDENCE_HELDOUT,
    )
    assert p0_normal.report.max_unilateral_deviation == 0.17
    assert p0_normal.report.p1_max_deviation_gain is None

    p1_normal = collect_normal_route_evidence(
        DummyOracle(),
        HUContinuationState(0, 14, 0),
        zero_continuation_values(),
        (
            HeldoutNormalSeedMetric("a", 20, -0.2, p1_deviation_gain=0.13),
            HeldoutNormalSeedMetric("b", 20, 0.2, p1_deviation_gain=0.19),
        ),
        implementation_sha256=IMPL_SHA,
        reference_evaluator_sha256=EVALUATOR_SHA,
        reference_authority="one-sided-reference-test",
        training_seed_ids=("train",),
        provenance="p1 normal fixture",
        evidence_kind=EVIDENCE_HELDOUT,
    )
    assert p1_normal.report.max_unilateral_deviation == 0.19
    assert p1_normal.report.p0_max_deviation_gain is None


def test_real_evidence_rejects_training_seed_overlap() -> None:
    with pytest.raises(ValueError, match="overlap"):
        collect_normal_route_evidence(
            DummyOracle(),
            HUContinuationState(0, 0, 0),
            zero_continuation_values(),
            nn_rows(),
            implementation_sha256=IMPL_SHA,
            reference_evaluator_sha256=EVALUATOR_SHA,
            reference_authority="reference",
            training_seed_ids=("heldout-a",),
            provenance="overlap fixture",
            evidence_kind=EVIDENCE_HELDOUT,
        )


def test_real_evidence_requires_multiple_heldout_seeds_and_training_provenance() -> None:
    single = (
        HeldoutNormalSeedMetric(
            "heldout-only",
            10,
            0.0,
            p0_deviation_gain=0.1,
            p1_deviation_gain=0.1,
        ),
    )
    with pytest.raises(ValueError, match="at least two"):
        collect_normal_route_evidence(
            DummyOracle(),
            HUContinuationState(0, 0, 0),
            zero_continuation_values(),
            single,
            implementation_sha256=IMPL_SHA,
            reference_evaluator_sha256=EVALUATOR_SHA,
            reference_authority="reference",
            training_seed_ids=("train",),
            provenance="single heldout fixture",
            evidence_kind=EVIDENCE_HELDOUT,
        )

    with pytest.raises(ValueError, match="training seed provenance"):
        collect_normal_route_evidence(
            DummyOracle(),
            HUContinuationState(0, 0, 0),
            zero_continuation_values(),
            nn_rows(),
            implementation_sha256=IMPL_SHA,
            reference_evaluator_sha256=EVALUATOR_SHA,
            reference_authority="reference",
            training_seed_ids=(),
            provenance="missing training provenance",
            evidence_kind=EVIDENCE_HELDOUT,
        )


def test_missing_required_deviation_fails_closed() -> None:
    rows = (
        HeldoutNormalSeedMetric("a", 10, 0.0, p0_deviation_gain=0.1),
        HeldoutNormalSeedMetric("b", 10, 0.0, p0_deviation_gain=0.1),
    )
    with pytest.raises(ValueError, match="missing P1"):
        collect_normal_route_evidence(
            DummyOracle(),
            HUContinuationState(0, 0, 0),
            zero_continuation_values(),
            rows,
            implementation_sha256=IMPL_SHA,
            reference_evaluator_sha256=EVALUATOR_SHA,
            reference_authority="reference",
            training_seed_ids=("train",),
            provenance="missing P1 fixture",
            evidence_kind=EVIDENCE_HELDOUT,
        )


def test_unequal_seed_sample_budgets_fail_closed() -> None:
    rows = (
        HeldoutNormalSeedMetric("a", 10, 0.0, 0.1, 0.1),
        HeldoutNormalSeedMetric("b", 11, 0.0, 0.1, 0.1),
    )
    with pytest.raises(ValueError, match="equal per-seed"):
        collect_normal_route_evidence(
            DummyOracle(),
            HUContinuationState(0, 0, 0),
            zero_continuation_values(),
            rows,
            implementation_sha256=IMPL_SHA,
            reference_evaluator_sha256=EVALUATOR_SHA,
            reference_authority="reference",
            training_seed_ids=("train",),
            provenance="unequal budget fixture",
            evidence_kind=EVIDENCE_HELDOUT,
        )


def test_continuation_and_reference_identity_are_sha_bound() -> None:
    base = collect_nn()
    changed_values = dict(zero_continuation_values())
    changed_state = next(iter(changed_values))
    changed_values[changed_state] = 0.125
    changed = collect_normal_route_evidence(
        DummyOracle(),
        HUContinuationState(0, 0, 0),
        changed_values,
        nn_rows(),
        implementation_sha256=IMPL_SHA,
        reference_evaluator_sha256=EVALUATOR_SHA,
        reference_authority="independent-reference-test",
        training_seed_ids=("train-1", "train-2"),
        provenance="m5h deterministic unit fixture",
        evidence_kind=EVIDENCE_HELDOUT,
    )
    assert changed.report.continuation_sha256 != base.report.continuation_sha256
    assert changed.report.sha256 != base.report.sha256
    assert changed.route_evidence.sha256 != base.route_evidence.sha256

    changed_reference = collect_normal_route_evidence(
        DummyOracle(),
        HUContinuationState(0, 0, 0),
        zero_continuation_values(),
        nn_rows(),
        implementation_sha256=IMPL_SHA,
        reference_evaluator_sha256="c" * 64,
        reference_authority="independent-reference-test",
        training_seed_ids=("train-1", "train-2"),
        provenance="m5h deterministic unit fixture",
        evidence_kind=EVIDENCE_HELDOUT,
    )
    assert changed_reference.report.sha256 != base.report.sha256
    assert changed_reference.route_evidence.sha256 != base.route_evidence.sha256


def test_synthetic_fixture_stays_test_only() -> None:
    result = collect_nn(evidence_kind=EVIDENCE_TEST)
    assert result.report.evidence_kind == EVIDENCE_TEST
    assert result.route_evidence.evidence_kind == EVIDENCE_TEST
