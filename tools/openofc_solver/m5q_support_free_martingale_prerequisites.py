from __future__ import annotations

"""Fail-closed prerequisite audit for a support-free MCCFR concentration route."""

import ast
from dataclasses import asdict, dataclass
import hashlib
import inspect
import json
import math
import textwrap
from typing import Iterable

from deepofc.hu_two_round import HUTwoRoundSubgame
from deepofc.hu_two_round_mccfr import TwoRoundExternalSamplingMCCFR
from m5q_support_range_feasibility import exact_terminal_utility_range

SCHEMA = "openofc-m5q-support-free-martingale-prerequisites-v1"
AUTHORITY = "SUPPORT_FREE_MARTINGALE_PREREQUISITE_AUDIT_NOT_CERTIFICATION"
M5Q_A_UNBIASEDNESS_PAYLOAD_SHA256 = (
    "0188c219f6946055b8dae8c350ebfbca7aef65c93403dbb5f79c793cf30cedf5"
)


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _contains_division(function) -> bool:
    source = textwrap.dedent(inspect.getsource(function))
    tree = ast.parse(source)
    return any(isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div) for node in ast.walk(tree))


def sampled_regret_path_has_explicit_division() -> bool:
    """Audit the production traversal/regret-accumulation path for `/` operators.

    This is deliberately structural.  It is not a proof that no hidden helper can
    ever introduce a probability correction; it binds the current concrete
    two-round External Sampling implementation audited by M5Q.
    """

    methods: Iterable = (
        TwoRoundExternalSamplingMCCFR._accumulate_regret,
        TwoRoundExternalSamplingMCCFR._stage_round4_second,
        TwoRoundExternalSamplingMCCFR._stage_round4_first,
        TwoRoundExternalSamplingMCCFR._stage_round3_second,
        TwoRoundExternalSamplingMCCFR._stage_round3_first,
        TwoRoundExternalSamplingMCCFR._sampled_traversal,
    )
    return any(_contains_division(method) for method in methods)


@dataclass(frozen=True)
class SupportFreeFamilyPrerequisite:
    family_id: str
    minimum_terminal_utility: float
    maximum_terminal_utility: float
    exact_utility_range: float
    sampled_regret_coordinate_abs_envelope: float
    envelope_derivation: str

    def payload(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SupportFreePrerequisiteReport:
    families: tuple[SupportFreeFamilyPrerequisite, ...]
    sampled_regret_path_has_explicit_inverse_weight_candidate: bool
    m5q_a_unbiasedness_payload_sha256: str
    unbiasedness_binding_status: str
    available_average_profile_methods: tuple[str, ...]
    theorem_compatible_reach_weighted_average_available: bool
    predictable_variance_accounting_available: bool
    bounded_increment_prerequisite_pass: bool
    support_free_certificate_prerequisites_complete: bool
    next_blocker: str
    authority: str = AUTHORITY
    schema: str = SCHEMA
    production_certification_eligible: bool = False
    real_routes_certified: int = 0
    sha256: str = ""

    def unsigned_payload(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "authority": self.authority,
            "families": [row.payload() for row in self.families],
            "sampled_regret_path_has_explicit_inverse_weight_candidate": self.sampled_regret_path_has_explicit_inverse_weight_candidate,
            "m5q_a_unbiasedness_payload_sha256": self.m5q_a_unbiasedness_payload_sha256,
            "unbiasedness_binding_status": self.unbiasedness_binding_status,
            "available_average_profile_methods": list(self.available_average_profile_methods),
            "theorem_compatible_reach_weighted_average_available": self.theorem_compatible_reach_weighted_average_available,
            "predictable_variance_accounting_available": self.predictable_variance_accounting_available,
            "bounded_increment_prerequisite_pass": self.bounded_increment_prerequisite_pass,
            "support_free_certificate_prerequisites_complete": self.support_free_certificate_prerequisites_complete,
            "next_blocker": self.next_blocker,
            "production_certification_eligible": self.production_certification_eligible,
            "real_routes_certified": self.real_routes_certified,
        }

    def payload(self) -> dict[str, object]:
        payload = self.unsigned_payload()
        payload["sha256"] = self.sha256
        return payload


def audit_support_free_prerequisites(
    families: Iterable[tuple[str, HUTwoRoundSubgame]],
) -> SupportFreePrerequisiteReport:
    rows: list[SupportFreeFamilyPrerequisite] = []
    for family_id, game in families:
        exact = exact_terminal_utility_range(game)
        delta = float(exact.utility_range)
        if not math.isfinite(delta) or delta <= 0.0:
            raise RuntimeError("support-free audit requires a finite positive utility range")
        # Every traverser action value and its regret-matching node value are
        # expectations/terminal values inside [u_min,u_max].  Their difference
        # is therefore bounded in absolute value by u_max-u_min = Delta_u.
        rows.append(
            SupportFreeFamilyPrerequisite(
                family_id=str(family_id),
                minimum_terminal_utility=float(exact.minimum_p0_utility),
                maximum_terminal_utility=float(exact.maximum_p0_utility),
                exact_utility_range=delta,
                sampled_regret_coordinate_abs_envelope=delta,
                envelope_derivation="|action_value-node_value| <= max_u-min_u",
            )
        )

    inverse_candidate = sampled_regret_path_has_explicit_division()
    average_methods = tuple(
        sorted(
            name
            for name in dir(TwoRoundExternalSamplingMCCFR)
            if "average" in name.lower() and "profile" in name.lower()
        )
    )
    # The production class explicitly labels behavioral_time_average_profile as
    # not a CFR average.  Do not infer theorem compatibility from its existence.
    reach_weighted = any(
        name in {
            "cfr_average_profile",
            "reach_weighted_average_profile",
            "cfr_reach_weighted_average_profile",
        }
        for name in average_methods
    )
    predictable_variance = any(
        hasattr(TwoRoundExternalSamplingMCCFR, name)
        for name in (
            "predictable_variance",
            "predictable_variance_process",
            "conditional_regret_variance",
        )
    )
    bounded_pass = (not inverse_candidate) and all(
        row.sampled_regret_coordinate_abs_envelope > 0.0 for row in rows
    )
    complete = bounded_pass and reach_weighted and predictable_variance
    if not reach_weighted:
        next_blocker = "THEOREM_COMPATIBLE_REACH_WEIGHTED_AVERAGE_MISSING"
    elif not predictable_variance:
        next_blocker = "PREDICTABLE_VARIANCE_ACCOUNTING_MISSING"
    elif inverse_candidate:
        next_blocker = "SAMPLED_REGRET_PATH_CONTAINS_DIVISION_REQUIRING_MANUAL_AUDIT"
    else:
        next_blocker = "NONE_PREREQUISITES_COMPLETE_BUT_NO_BOUND_INSTANTIATED"

    unsigned: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "families": [row.payload() for row in rows],
        "sampled_regret_path_has_explicit_inverse_weight_candidate": inverse_candidate,
        "m5q_a_unbiasedness_payload_sha256": M5Q_A_UNBIASEDNESS_PAYLOAD_SHA256,
        "unbiasedness_binding_status": "FINITE_MONTE_CARLO_DIAGNOSTIC_NOT_PROOF",
        "available_average_profile_methods": list(average_methods),
        "theorem_compatible_reach_weighted_average_available": reach_weighted,
        "predictable_variance_accounting_available": predictable_variance,
        "bounded_increment_prerequisite_pass": bounded_pass,
        "support_free_certificate_prerequisites_complete": complete,
        "next_blocker": next_blocker,
        "production_certification_eligible": False,
        "real_routes_certified": 0,
    }
    return SupportFreePrerequisiteReport(
        families=tuple(rows),
        sampled_regret_path_has_explicit_inverse_weight_candidate=inverse_candidate,
        m5q_a_unbiasedness_payload_sha256=M5Q_A_UNBIASEDNESS_PAYLOAD_SHA256,
        unbiasedness_binding_status="FINITE_MONTE_CARLO_DIAGNOSTIC_NOT_PROOF",
        available_average_profile_methods=average_methods,
        theorem_compatible_reach_weighted_average_available=reach_weighted,
        predictable_variance_accounting_available=predictable_variance,
        bounded_increment_prerequisite_pass=bounded_pass,
        support_free_certificate_prerequisites_complete=complete,
        next_blocker=next_blocker,
        sha256=_sha(unsigned),
    )
