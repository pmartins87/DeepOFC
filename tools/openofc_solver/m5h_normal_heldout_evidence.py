from __future__ import annotations

"""Independent held-out evidence aggregation for Normal-hand M5C routes.

M5H deliberately separates three concerns:

* the candidate policy/oracle is built elsewhere (M5A/M5B);
* an independently identified reference evaluator measures unilateral deviation;
* this module seals held-out seed metrics into the general M5C evidence schema.

No strategic acceptance threshold is inferred or applied here.
"""

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Mapping, Sequence

from fantasy_fantasy_payoff import continuation_fingerprint
from hu_continuation import (
    HUContinuationState,
    KERNEL_NORMAL_FANTASY,
    KERNEL_NORMAL_NORMAL,
    hand_kernel_kind,
)
from m5c_route_certification import (
    EVIDENCE_HELDOUT,
    EVIDENCE_TEST,
    HeldoutRouteEvidence,
    freeze_route_evidence,
)
from normal_fantasy_kernel import players_for_meta

REPORT_SCHEMA = "openofc-m5h-normal-heldout-report-v1"
AUTHORITY = "NORMAL_ROUTE_HELDOUT_EVIDENCE_PRODUCER_NOT_CERTIFIER"
SUPPORTED_KERNELS = (KERNEL_NORMAL_NORMAL, KERNEL_NORMAL_FANTASY)
EPS = 1e-12


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha(payload: Mapping[str, object]) -> str:
    raw = dict(payload)
    raw.pop("sha256", None)
    return hashlib.sha256(_canonical_bytes(raw)).hexdigest()


def _require_sha256(value: object, label: str) -> str:
    text = str(value).lower()
    if len(text) != 64:
        raise ValueError(f"{label} must be a SHA-256")
    try:
        int(text, 16)
    except ValueError as exc:
        raise ValueError(f"{label} must be a SHA-256") from exc
    return text


def _finite(value: object, label: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def _optional_nonnegative(value: float | None, label: str) -> float | None:
    if value is None:
        return None
    number = _finite(value, label)
    if number < -EPS:
        raise ValueError(f"{label} must be non-negative")
    return max(0.0, number)


@dataclass(frozen=True)
class HeldoutNormalSeedMetric:
    """One independently seeded route-evaluation aggregate.

    `profile_p0_value` is always from persistent P0 perspective. Deviation gains
    are positive improvements available to the named persistent player.
    """

    seed_id: str
    samples: int
    profile_p0_value: float
    p0_deviation_gain: float | None = None
    p1_deviation_gain: float | None = None

    def __post_init__(self) -> None:
        if not str(self.seed_id).strip():
            raise ValueError("M5H held-out seed id must be non-empty")
        if int(self.samples) <= 0:
            raise ValueError("M5H per-seed sample count must be positive")
        _finite(self.profile_p0_value, "profile_p0_value")
        _optional_nonnegative(self.p0_deviation_gain, "p0_deviation_gain")
        _optional_nonnegative(self.p1_deviation_gain, "p1_deviation_gain")


@dataclass(frozen=True)
class NormalRouteHeldoutReport:
    state: str
    kernel_kind: str
    oracle_id: str
    implementation_sha256: str
    continuation_sha256: str
    reference_evaluator_sha256: str
    reference_authority: str
    heldout_seed_ids: tuple[str, ...]
    training_seed_ids: tuple[str, ...]
    samples_per_seed: int
    heldout_samples: int
    mean_profile_p0_value: float
    value_standard_error: float
    p0_max_deviation_gain: float | None
    p1_max_deviation_gain: float | None
    max_unilateral_deviation: float
    evidence_kind: str
    provenance: str
    seed_metrics: tuple[HeldoutNormalSeedMetric, ...]
    sha256: str
    schema: str = REPORT_SCHEMA
    authority: str = AUTHORITY
    promotion_blocked: bool = True


@dataclass(frozen=True)
class NormalEvidenceBundle:
    report: NormalRouteHeldoutReport
    route_evidence: HeldoutRouteEvidence


def _mean_standard_error(values: Sequence[float]) -> tuple[float, float]:
    if len(values) < 2:
        # A one-seed synthetic fixture can exercise serialization, but a REAL
        # held-out object is rejected before reaching this helper.
        if not values:
            raise ValueError("M5H requires held-out profile values")
        return float(values[0]), 0.0
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    return float(mean), float(math.sqrt(max(0.0, variance) / len(values)))


def _required_deviators(state: HUContinuationState) -> tuple[int, ...]:
    kind = hand_kernel_kind(state)
    if kind == KERNEL_NORMAL_NORMAL:
        return (0, 1)
    if kind == KERNEL_NORMAL_FANTASY:
        normal_player, _fantasy_player = players_for_meta(state)
        return (int(normal_player),)
    raise ValueError("M5H only accepts Normal-hand route states")


def _metric_gain(row: HeldoutNormalSeedMetric, player: int) -> float | None:
    if player == 0:
        return _optional_nonnegative(row.p0_deviation_gain, "p0_deviation_gain")
    if player == 1:
        return _optional_nonnegative(row.p1_deviation_gain, "p1_deviation_gain")
    raise ValueError("persistent HU player must be 0 or 1")


def collect_normal_route_evidence(
    oracle: object,
    state: HUContinuationState,
    continuation_values: Mapping[HUContinuationState, float],
    heldout: Sequence[HeldoutNormalSeedMetric],
    *,
    implementation_sha256: str,
    reference_evaluator_sha256: str,
    reference_authority: str,
    training_seed_ids: Sequence[str],
    provenance: str,
    evidence_kind: str = EVIDENCE_TEST,
) -> NormalEvidenceBundle:
    """Seal independent Normal-route metrics into the general M5C evidence type.

    Thresholds are intentionally absent. A caller must separately pass the
    returned `HeldoutRouteEvidence` to M5C with an independently frozen
    `StrategicThresholdManifest`.
    """

    kind = hand_kernel_kind(state)
    if kind not in SUPPORTED_KERNELS:
        raise ValueError("M5H only evaluates Normal/Normal or Normal/Fantasy routes")
    oracle_id = str(getattr(oracle, "oracle_id", "")).strip()
    if not oracle_id:
        raise ValueError("M5H oracle must expose a non-empty oracle_id")
    implementation_sha = _require_sha256(
        implementation_sha256, "implementation_sha256"
    )
    evaluator_sha = _require_sha256(
        reference_evaluator_sha256, "reference_evaluator_sha256"
    )
    authority = str(reference_authority).strip()
    provenance_text = str(provenance).strip()
    if not authority or not provenance_text:
        raise ValueError("M5H requires reference authority and provenance")
    if evidence_kind not in (EVIDENCE_HELDOUT, EVIDENCE_TEST):
        raise ValueError("M5H evidence_kind must be HELD_OUT or SYNTHETIC_TEST_ONLY")

    rows = tuple(heldout)
    if not rows:
        raise ValueError("M5H requires held-out seed metrics")
    seed_ids = tuple(str(row.seed_id).strip() for row in rows)
    if len(set(seed_ids)) != len(seed_ids):
        raise ValueError("M5H held-out seed ids must be unique")

    train_ids = tuple(str(seed).strip() for seed in training_seed_ids)
    if any(not seed for seed in train_ids) or len(set(train_ids)) != len(train_ids):
        raise ValueError("M5H training seed ids must be unique and non-empty when supplied")
    overlap = sorted(set(seed_ids) & set(train_ids))
    if overlap:
        raise ValueError(f"M5H training/held-out seed overlap: {overlap[:3]}")
    if evidence_kind == EVIDENCE_HELDOUT:
        if len(rows) < 2:
            raise ValueError("REAL M5H held-out evidence requires at least two independent seeds")
        if not train_ids:
            raise ValueError("REAL M5H held-out evidence requires training seed provenance")

    per_seed_samples = {int(row.samples) for row in rows}
    if len(per_seed_samples) != 1:
        raise ValueError(
            "M5H requires equal per-seed sample budgets for seed-level uncertainty"
        )
    samples_per_seed = next(iter(per_seed_samples))

    required = _required_deviators(state)
    for row in rows:
        for player in required:
            if _metric_gain(row, player) is None:
                raise ValueError(
                    f"M5H route {state.as_key()} is missing P{player} unilateral-deviation evidence"
                )

    # Sort by explicit seed identity so report identity does not depend on input
    # iteration order.
    rows = tuple(sorted(rows, key=lambda row: str(row.seed_id)))
    seed_ids = tuple(str(row.seed_id) for row in rows)
    train_ids = tuple(sorted(train_ids))

    p0_gains = [
        gain
        for row in rows
        if (gain := _metric_gain(row, 0)) is not None
    ]
    p1_gains = [
        gain
        for row in rows
        if (gain := _metric_gain(row, 1)) is not None
    ]
    p0_max = max(p0_gains) if p0_gains else None
    p1_max = max(p1_gains) if p1_gains else None
    required_gains = [
        gain
        for player in required
        for row in rows
        if (gain := _metric_gain(row, player)) is not None
    ]
    if not required_gains:
        raise AssertionError("M5H produced no required unilateral-deviation metric")
    max_deviation = max(required_gains)

    profile_values = [float(row.profile_p0_value) for row in rows]
    mean_value, standard_error = _mean_standard_error(profile_values)
    heldout_samples = len(rows) * samples_per_seed
    _checked, continuation_sha = continuation_fingerprint(continuation_values)

    payload: dict[str, object] = {
        "schema": REPORT_SCHEMA,
        "authority": AUTHORITY,
        "state": state.as_key(),
        "kernel_kind": kind,
        "oracle_id": oracle_id,
        "implementation_sha256": implementation_sha,
        "continuation_sha256": continuation_sha,
        "reference_evaluator_sha256": evaluator_sha,
        "reference_authority": authority,
        "heldout_seed_ids": list(seed_ids),
        "training_seed_ids": list(train_ids),
        "samples_per_seed": samples_per_seed,
        "heldout_samples": heldout_samples,
        "mean_profile_p0_value": mean_value,
        "value_standard_error": standard_error,
        "p0_max_deviation_gain": p0_max,
        "p1_max_deviation_gain": p1_max,
        "max_unilateral_deviation": max_deviation,
        "evidence_kind": evidence_kind,
        "provenance": provenance_text,
        "seed_metrics": [
            {
                "seed_id": row.seed_id,
                "samples": int(row.samples),
                "profile_p0_value": float(row.profile_p0_value),
                "p0_deviation_gain": row.p0_deviation_gain,
                "p1_deviation_gain": row.p1_deviation_gain,
            }
            for row in rows
        ],
        "promotion_blocked": True,
    }
    report_sha = _sha(payload)
    report = NormalRouteHeldoutReport(
        state=state.as_key(),
        kernel_kind=kind,
        oracle_id=oracle_id,
        implementation_sha256=implementation_sha,
        continuation_sha256=continuation_sha,
        reference_evaluator_sha256=evaluator_sha,
        reference_authority=authority,
        heldout_seed_ids=seed_ids,
        training_seed_ids=train_ids,
        samples_per_seed=samples_per_seed,
        heldout_samples=heldout_samples,
        mean_profile_p0_value=mean_value,
        value_standard_error=standard_error,
        p0_max_deviation_gain=p0_max,
        p1_max_deviation_gain=p1_max,
        max_unilateral_deviation=max_deviation,
        evidence_kind=evidence_kind,
        provenance=provenance_text,
        seed_metrics=rows,
        sha256=report_sha,
    )

    evidence = freeze_route_evidence(
        state=state,
        oracle_id=oracle_id,
        implementation_sha256=implementation_sha,
        continuation_evidence_sha256=continuation_sha,
        heldout_seed_ids=seed_ids,
        heldout_samples=heldout_samples,
        value_standard_error=standard_error,
        max_unilateral_deviation=max_deviation,
        evidence_kind=evidence_kind,
        provenance=(
            f"{provenance_text} | {AUTHORITY} report={report_sha} "
            f"reference={authority} evaluator_sha256={evaluator_sha}"
        ),
    )
    return NormalEvidenceBundle(report=report, route_evidence=evidence)
