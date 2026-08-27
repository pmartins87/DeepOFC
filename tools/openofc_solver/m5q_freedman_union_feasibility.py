from __future__ import annotations

"""Conservative coordinate-wise Freedman feasibility accounting for M5Q.

This module evaluates a deliberately coarse support-free certificate architecture:
one-sided Freedman concentration is union-bounded over every sampled regret
action-coordinate; predictable quadratic variation is bounded only from the
exact terminal utility range.  It is a feasibility screen, not a route
certificate and not the final martingale construction.
"""

from dataclasses import asdict, dataclass
import hashlib
import json
import math

from deepofc.hu_two_round import HUTwoRoundSubgame
from m5q_support_range_feasibility import exact_terminal_utility_range

SCHEMA = "openofc-m5q-freedman-union-feasibility-v1"
AUTHORITY = "COORDINATE_FREEDMAN_UNION_FEASIBILITY_NOT_CERTIFICATION"
THEOREM_SOURCE = "Freedman scalar martingale inequality; predictable quadratic variation form"
REGRET_BRIDGE_SOURCE = "Zinkevich-Johanson-Bowling-Piccione 2007 counterfactual-regret decomposition"


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


@dataclass(frozen=True)
class FamilyStructure:
    family_id: str
    player0_infosets: int
    player1_infosets: int
    total_infosets: int
    action_coordinates: int
    utility_range: float
    sampled_regret_abs_envelope: float
    martingale_difference_upper_envelope: float
    per_iteration_variance_upper_bound: float

    def payload(self) -> dict[str, object]:
        return asdict(self)


def family_structure(family_id: str, game: HUTwoRoundSubgame) -> FamilyStructure:
    exact = exact_terminal_utility_range(game)
    delta = float(exact.utility_range)
    infos = [0, 0]
    coordinates = 0
    for info, actions in game.info_actions.items():
        infos[info.player] += 1
        coordinates += len(actions)
    if coordinates <= 0 or min(infos) <= 0:
        raise RuntimeError("Freedman feasibility requires nonempty player information surfaces")
    # Sampled coordinate increment rhat lies in [-Delta_u, +Delta_u].  The
    # martingale difference E[rhat|F]-rhat is therefore upper-bounded by 2Delta_u.
    # Popoviciu gives Var(rhat|F) <= (2Delta_u)^2/4 = Delta_u^2.
    return FamilyStructure(
        family_id=str(family_id),
        player0_infosets=infos[0],
        player1_infosets=infos[1],
        total_infosets=infos[0] + infos[1],
        action_coordinates=coordinates,
        utility_range=delta,
        sampled_regret_abs_envelope=delta,
        martingale_difference_upper_envelope=2.0 * delta,
        per_iteration_variance_upper_bound=delta * delta,
    )


def freedman_coordinate_radius(
    *,
    iterations: int,
    familywise_failure_probability: float,
    action_coordinates: int,
    martingale_difference_upper_envelope: float,
    per_iteration_variance_upper_bound: float,
) -> float:
    if iterations <= 0:
        raise ValueError("iterations must be positive")
    alpha = float(familywise_failure_probability)
    if not 0.0 < alpha < 1.0:
        raise ValueError("familywise failure probability must be in (0,1)")
    if action_coordinates <= 0:
        raise ValueError("action_coordinates must be positive")
    r = float(martingale_difference_upper_envelope)
    variance = float(per_iteration_variance_upper_bound)
    if not math.isfinite(r) or not math.isfinite(variance) or r <= 0.0 or variance <= 0.0:
        raise ValueError("Freedman envelopes must be finite and positive")

    # One-sided union bound: p = alpha / number of action coordinates.
    log_term = math.log(float(action_coordinates) / alpha)
    predictable_variation = float(iterations) * variance
    linear = r * log_term / 3.0
    return linear + math.sqrt(linear * linear + 2.0 * predictable_variation * log_term)


def zero_sampled_positive_regret_contribution(
    structure: FamilyStructure,
    *,
    iterations: int,
    familywise_failure_probability: float,
) -> float:
    """Additive exploitability term of this coarse certificate architecture.

    This uses the standard safe relaxation
      max_a (sampled_R(I,a) + radius)^+ <= max_a sampled_R(I,a)^+ + radius.
    Setting the sampled-positive-regret term to zero isolates only the mandatory
    concentration penalty introduced by this particular relaxation.
    """

    radius = freedman_coordinate_radius(
        iterations=iterations,
        familywise_failure_probability=familywise_failure_probability,
        action_coordinates=structure.action_coordinates,
        martingale_difference_upper_envelope=structure.martingale_difference_upper_envelope,
        per_iteration_variance_upper_bound=structure.per_iteration_variance_upper_bound,
    )
    return structure.total_infosets * radius / (2.0 * float(iterations))


def required_iterations_for_concentration_contribution(
    structure: FamilyStructure,
    *,
    target_exploitability: float,
    familywise_failure_probability: float,
) -> int:
    target = float(target_exploitability)
    if not math.isfinite(target) or target <= 0.0:
        raise ValueError("target exploitability must be finite and positive")

    def passes(iterations: int) -> bool:
        return zero_sampled_positive_regret_contribution(
            structure,
            iterations=iterations,
            familywise_failure_probability=familywise_failure_probability,
        ) <= target

    hi = 1
    while not passes(hi):
        hi *= 2
        if hi > 10**30:
            raise RuntimeError("Freedman feasibility search exceeded 1e30 iterations")
    lo = 1
    while lo < hi:
        mid = (lo + hi) // 2
        if passes(mid):
            hi = mid
        else:
            lo = mid + 1
    return lo


@dataclass(frozen=True)
class FreedmanUnionFamilyResult:
    structure: FamilyStructure
    familywise_failure_probability: float
    target_exploitability: float
    probe_iterations: int
    coordinate_radius_at_probe: float
    concentration_only_exploitability_at_probe: float
    required_iterations_for_target_concentration_only: int

    def payload(self) -> dict[str, object]:
        return {
            "structure": self.structure.payload(),
            "familywise_failure_probability": self.familywise_failure_probability,
            "target_exploitability": self.target_exploitability,
            "probe_iterations": self.probe_iterations,
            "coordinate_radius_at_probe": self.coordinate_radius_at_probe,
            "concentration_only_exploitability_at_probe": self.concentration_only_exploitability_at_probe,
            "required_iterations_for_target_concentration_only": self.required_iterations_for_target_concentration_only,
        }


def evaluate_family(
    family_id: str,
    game: HUTwoRoundSubgame,
    *,
    target_exploitability: float,
    familywise_failure_probability: float,
    probe_iterations: int,
) -> FreedmanUnionFamilyResult:
    structure = family_structure(family_id, game)
    radius = freedman_coordinate_radius(
        iterations=probe_iterations,
        familywise_failure_probability=familywise_failure_probability,
        action_coordinates=structure.action_coordinates,
        martingale_difference_upper_envelope=structure.martingale_difference_upper_envelope,
        per_iteration_variance_upper_bound=structure.per_iteration_variance_upper_bound,
    )
    contribution = zero_sampled_positive_regret_contribution(
        structure,
        iterations=probe_iterations,
        familywise_failure_probability=familywise_failure_probability,
    )
    required = required_iterations_for_concentration_contribution(
        structure,
        target_exploitability=target_exploitability,
        familywise_failure_probability=familywise_failure_probability,
    )
    return FreedmanUnionFamilyResult(
        structure=structure,
        familywise_failure_probability=float(familywise_failure_probability),
        target_exploitability=float(target_exploitability),
        probe_iterations=int(probe_iterations),
        coordinate_radius_at_probe=radius,
        concentration_only_exploitability_at_probe=contribution,
        required_iterations_for_target_concentration_only=required,
    )


def report_payload(results: tuple[FreedmanUnionFamilyResult, ...]) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "theorem_source": THEOREM_SOURCE,
        "regret_bridge_source": REGRET_BRIDGE_SOURCE,
        "families": [row.payload() for row in results],
        "predictable_variance_accounting_kind": "POPOVICIU_WORST_CASE_DELTA_U_SQUARED_PER_ITERATION",
        "coordinate_concentration_kind": "ONE_SIDED_FREEDMAN_PLUS_UNION_BOUND",
        "sampled_positive_regret_term_assumed_zero_for_feasibility": True,
        "production_certification_eligible": False,
        "real_routes_certified": 0,
    }
    payload["sha256"] = _sha(payload)
    return payload
