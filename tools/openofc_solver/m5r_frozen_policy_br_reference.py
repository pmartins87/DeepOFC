from __future__ import annotations

"""Exact reduced-game frozen-policy best-response reference for M5R.

The authority in this module is deliberately scoped to the exact enumerable
`HUTwoRoundSubgame` family.  It provides a reference against which future
scalable deviation evaluators can be validated; it does not certify any full
OpenOFC continuation route.
"""

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Iterable

from deepofc.hu_two_round import HUTwoRoundSubgame, StrategyProfile
from deepofc.hu_two_round_br import (
    exact_best_response,
    profile_with_pure_response,
)

REFERENCE_SCHEMA = "openofc-m5r-exact-reduced-frozen-policy-br-v1"
REFERENCE_AUTHORITY = "EXACT_REDUCED_TWO_ROUND_FROZEN_POLICY_BEST_RESPONSE_REFERENCE"
VALIDATION_SCHEMA = "openofc-m5r-exact-br-reference-validation-v1"
MANIFEST_SCHEMA = "openofc-m5r-reference-evaluator-manifest-v1"
MANIFEST_AUTHORITY = "REFERENCE_EVALUATOR_MANIFEST_NOT_ROUTE_CERTIFICATION"
REDUCED_SCOPE = "EXACT_ENUMERATED_TWO_ROUND_PERFECT_RECALL_REDUCED_GAMES"


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _require_sha256(value: str, label: str) -> str:
    text = str(value).lower()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise ValueError(f"{label} must be a lowercase SHA-256 hex digest")
    return text


def frozen_policy_payload(
    game: HUTwoRoundSubgame,
    profile: StrategyProfile,
) -> dict[str, object]:
    """Return a complete deterministic normalized policy representation."""

    rows: list[dict[str, object]] = []
    infos = sorted(
        game.info_actions,
        key=lambda info: _canonical_bytes(asdict(info)),
    )
    for info in infos:
        distribution = game._distribution(profile, info)
        actions = sorted(
            game.actions(info),
            key=lambda action: _canonical_bytes(action.key()),
        )
        rows.append(
            {
                "info": asdict(info),
                "actions": [
                    {
                        "action_key": action.key(),
                        "probability": float(distribution[action]),
                    }
                    for action in actions
                ],
            }
        )
    payload: dict[str, object] = {
        "schema": "openofc-m5r-frozen-reduced-policy-v1",
        "infosets": rows,
    }
    payload["sha256"] = _sha(payload)
    return payload


@dataclass(frozen=True)
class ExactFrozenPolicyBRReport:
    family_id: str
    profile_sha256: str
    infosets: int
    expected_p0_utility: float
    br0_value: float
    br1_value: float
    p0_deviation_gain: float
    p1_deviation_gain: float
    max_unilateral_deviation_gain: float
    nash_conv: float
    exploitability: float
    br0_infosets: int
    br1_infosets: int
    independent_br0_p0_value: float
    independent_br1_p1_value: float
    independent_value_crosscheck_max_abs_error: float
    authority: str = REFERENCE_AUTHORITY
    schema: str = REFERENCE_SCHEMA
    production_certification_eligible: bool = False
    real_routes_certified: int = 0
    sha256: str = ""

    def unsigned_payload(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "authority": self.authority,
            "family_id": self.family_id,
            "profile_sha256": self.profile_sha256,
            "infosets": self.infosets,
            "expected_p0_utility": self.expected_p0_utility,
            "br0_value": self.br0_value,
            "br1_value": self.br1_value,
            "p0_deviation_gain": self.p0_deviation_gain,
            "p1_deviation_gain": self.p1_deviation_gain,
            "max_unilateral_deviation_gain": self.max_unilateral_deviation_gain,
            "nash_conv": self.nash_conv,
            "exploitability": self.exploitability,
            "br0_infosets": self.br0_infosets,
            "br1_infosets": self.br1_infosets,
            "independent_br0_p0_value": self.independent_br0_p0_value,
            "independent_br1_p1_value": self.independent_br1_p1_value,
            "independent_value_crosscheck_max_abs_error": self.independent_value_crosscheck_max_abs_error,
            "production_certification_eligible": self.production_certification_eligible,
            "real_routes_certified": self.real_routes_certified,
        }

    def payload(self) -> dict[str, object]:
        payload = self.unsigned_payload()
        payload["sha256"] = self.sha256
        return payload


def evaluate_frozen_policy_exact_br(
    family_id: str,
    game: HUTwoRoundSubgame,
    profile: StrategyProfile,
) -> ExactFrozenPolicyBRReport:
    frozen = frozen_policy_payload(game, profile)
    expected = float(game.expected_u0(profile))
    br0 = exact_best_response(game, profile, 0)
    br1 = exact_best_response(game, profile, 1)

    # Independent expected-value traversal with the exact pure response
    # materialized into a complete profile.
    p0_response_profile = profile_with_pure_response(game, profile, br0)
    p1_response_profile = profile_with_pure_response(game, profile, br1)
    independent_br0_p0 = float(game.expected_u0(p0_response_profile))
    independent_br1_p1 = -float(game.expected_u0(p1_response_profile))
    cross_error = max(
        abs(float(br0.value) - independent_br0_p0),
        abs(float(br1.value) - independent_br1_p1),
    )

    gain0 = float(br0.value) - expected
    gain1 = float(br1.value) + expected
    nash_conv = gain0 + gain1
    exploitability = 0.5 * nash_conv
    if gain0 < -1e-12 or gain1 < -1e-12:
        raise AssertionError("exact best response cannot underperform the frozen profile")
    if cross_error > 1e-12:
        raise AssertionError("exact BR disagrees with independent expected-value traversal")

    unsigned: dict[str, object] = {
        "schema": REFERENCE_SCHEMA,
        "authority": REFERENCE_AUTHORITY,
        "family_id": str(family_id),
        "profile_sha256": str(frozen["sha256"]),
        "infosets": len(game.info_actions),
        "expected_p0_utility": expected,
        "br0_value": float(br0.value),
        "br1_value": float(br1.value),
        "p0_deviation_gain": gain0,
        "p1_deviation_gain": gain1,
        "max_unilateral_deviation_gain": max(gain0, gain1),
        "nash_conv": nash_conv,
        "exploitability": exploitability,
        "br0_infosets": len(br0.choices),
        "br1_infosets": len(br1.choices),
        "independent_br0_p0_value": independent_br0_p0,
        "independent_br1_p1_value": independent_br1_p1,
        "independent_value_crosscheck_max_abs_error": cross_error,
        "production_certification_eligible": False,
        "real_routes_certified": 0,
    }
    return ExactFrozenPolicyBRReport(
        family_id=str(family_id),
        profile_sha256=str(frozen["sha256"]),
        infosets=len(game.info_actions),
        expected_p0_utility=expected,
        br0_value=float(br0.value),
        br1_value=float(br1.value),
        p0_deviation_gain=gain0,
        p1_deviation_gain=gain1,
        max_unilateral_deviation_gain=max(gain0, gain1),
        nash_conv=nash_conv,
        exploitability=exploitability,
        br0_infosets=len(br0.choices),
        br1_infosets=len(br1.choices),
        independent_br0_p0_value=independent_br0_p0,
        independent_br1_p1_value=independent_br1_p1,
        independent_value_crosscheck_max_abs_error=cross_error,
        sha256=_sha(unsigned),
    )


@dataclass(frozen=True)
class ExactReferenceValidation:
    rows: tuple[ExactFrozenPolicyBRReport, ...]
    validation_status: str
    maximum_crosscheck_abs_error: float
    validation_scope: str = REDUCED_SCOPE
    schema: str = VALIDATION_SCHEMA
    production_certification_eligible: bool = False
    real_routes_certified: int = 0
    sha256: str = ""

    def unsigned_payload(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "validation_scope": self.validation_scope,
            "validation_status": self.validation_status,
            "rows": [row.payload() for row in self.rows],
            "maximum_crosscheck_abs_error": self.maximum_crosscheck_abs_error,
            "production_certification_eligible": self.production_certification_eligible,
            "real_routes_certified": self.real_routes_certified,
        }

    def payload(self) -> dict[str, object]:
        payload = self.unsigned_payload()
        payload["sha256"] = self.sha256
        return payload


def validate_exact_reference(
    cases: Iterable[tuple[str, HUTwoRoundSubgame, StrategyProfile]],
) -> ExactReferenceValidation:
    rows = tuple(
        evaluate_frozen_policy_exact_br(family_id, game, profile)
        for family_id, game, profile in cases
    )
    if not rows:
        raise ValueError("M5R reference validation requires at least one case")
    max_error = max(row.independent_value_crosscheck_max_abs_error for row in rows)
    status = "PASS" if max_error <= 1e-12 else "FAIL"
    unsigned: dict[str, object] = {
        "schema": VALIDATION_SCHEMA,
        "validation_scope": REDUCED_SCOPE,
        "validation_status": status,
        "rows": [row.payload() for row in rows],
        "maximum_crosscheck_abs_error": max_error,
        "production_certification_eligible": False,
        "real_routes_certified": 0,
    }
    return ExactReferenceValidation(
        rows=rows,
        validation_status=status,
        maximum_crosscheck_abs_error=max_error,
        sha256=_sha(unsigned),
    )


@dataclass(frozen=True)
class ReferenceEvaluatorManifest:
    evaluator_id: str
    implementation_sha256: str
    validation_evidence_sha256: str
    validation_status: str
    validation_scope: str
    evaluator_authority: str
    guaranteed_missed_deviation_upper_bound: float | None
    certification_eligible: bool
    provenance: str
    authority: str = MANIFEST_AUTHORITY
    schema: str = MANIFEST_SCHEMA
    production_route_certification_eligible: bool = False
    real_routes_certified: int = 0
    sha256: str = ""

    def unsigned_payload(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "authority": self.authority,
            "evaluator_id": self.evaluator_id,
            "implementation_sha256": self.implementation_sha256,
            "validation_evidence_sha256": self.validation_evidence_sha256,
            "validation_status": self.validation_status,
            "validation_scope": self.validation_scope,
            "evaluator_authority": self.evaluator_authority,
            "guaranteed_missed_deviation_upper_bound": self.guaranteed_missed_deviation_upper_bound,
            "certification_eligible": self.certification_eligible,
            "provenance": self.provenance,
            "production_route_certification_eligible": self.production_route_certification_eligible,
            "real_routes_certified": self.real_routes_certified,
        }

    def payload(self) -> dict[str, object]:
        payload = self.unsigned_payload()
        payload["sha256"] = self.sha256
        return payload


def freeze_reference_evaluator_manifest(
    *,
    evaluator_id: str,
    implementation_sha256: str,
    validation_evidence_sha256: str,
    validation_status: str,
    validation_scope: str,
    evaluator_authority: str,
    guaranteed_missed_deviation_upper_bound: float | None,
    certification_eligible: bool,
    provenance: str,
) -> ReferenceEvaluatorManifest:
    if not str(evaluator_id).strip():
        raise ValueError("M5R evaluator_id must be nonempty")
    implementation_sha256 = _require_sha256(implementation_sha256, "implementation_sha256")
    validation_evidence_sha256 = _require_sha256(
        validation_evidence_sha256, "validation_evidence_sha256"
    )
    if not str(validation_scope).strip() or not str(evaluator_authority).strip():
        raise ValueError("M5R evaluator scope/authority must be nonempty")
    if not str(provenance).strip():
        raise ValueError("M5R manifest provenance must be nonempty")
    if guaranteed_missed_deviation_upper_bound is not None:
        bound = float(guaranteed_missed_deviation_upper_bound)
        if not math.isfinite(bound) or bound < 0.0:
            raise ValueError("M5R missed-deviation bound must be finite and nonnegative")
    else:
        bound = None

    if certification_eligible:
        if str(validation_status) != "PASS":
            raise ValueError("certification-eligible evaluator requires PASS validation")
        if bound is None:
            raise ValueError(
                "certification-eligible evaluator requires guaranteed missed-deviation upper bound"
            )

    unsigned: dict[str, object] = {
        "schema": MANIFEST_SCHEMA,
        "authority": MANIFEST_AUTHORITY,
        "evaluator_id": str(evaluator_id),
        "implementation_sha256": implementation_sha256,
        "validation_evidence_sha256": validation_evidence_sha256,
        "validation_status": str(validation_status),
        "validation_scope": str(validation_scope),
        "evaluator_authority": str(evaluator_authority),
        "guaranteed_missed_deviation_upper_bound": bound,
        "certification_eligible": bool(certification_eligible),
        "provenance": str(provenance),
        "production_route_certification_eligible": False,
        "real_routes_certified": 0,
    }
    return ReferenceEvaluatorManifest(
        evaluator_id=str(evaluator_id),
        implementation_sha256=implementation_sha256,
        validation_evidence_sha256=validation_evidence_sha256,
        validation_status=str(validation_status),
        validation_scope=str(validation_scope),
        evaluator_authority=str(evaluator_authority),
        guaranteed_missed_deviation_upper_bound=bound,
        certification_eligible=bool(certification_eligible),
        provenance=str(provenance),
        sha256=_sha(unsigned),
    )
