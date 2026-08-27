from __future__ import annotations

"""Visit-weighted scalar Freedman feasibility on exact reduced-game profiles.

Unlike the earlier all-coordinate worst-case-PQV screen, this module assigns each
infoset the exact predictable External Sampling visit probability for a frozen
profile.  It still uses scalar coordinate bounds, a global action-coordinate
union bound, the Delta_u magnitude envelope and zero sampled positive regret.
It therefore isolates how much looseness is removed by structural visitation
alone without claiming a training-trajectory certificate.
"""

from dataclasses import dataclass
import math

from deepofc.hu_two_round import HUTwoRoundSubgame, StrategyProfile
from m5q_predictable_visit_variance import external_sampling_infoset_visit_probabilities

SCHEMA = "openofc-m5q-visit-weighted-freedman-feasibility-v1"
AUTHORITY = "VISIT_WEIGHTED_FREEDMAN_FEASIBILITY_NOT_CERTIFICATION"


def _radius(
    *,
    iterations: int,
    visit_probability: float,
    utility_range: float,
    log_union_term: float,
) -> float:
    if iterations <= 0:
        raise ValueError("iterations must be positive")
    p = float(visit_probability)
    if not 0.0 <= p <= 1.0:
        raise ValueError("visit probability must be in [0,1]")
    if p == 0.0:
        return 0.0
    delta = float(utility_range)
    if delta <= 0.0 or not math.isfinite(delta):
        raise ValueError("utility range must be finite and positive")
    if log_union_term <= 0.0 or not math.isfinite(log_union_term):
        raise ValueError("log union term must be finite and positive")
    r = 2.0 * delta
    variance = float(iterations) * p * delta * delta
    linear = r * log_union_term / 3.0
    return linear + math.sqrt(linear * linear + 2.0 * variance * log_union_term)


@dataclass(frozen=True)
class VisitWeightedFreedmanResult:
    family_id: str
    profile_id: str
    infosets: int
    action_coordinates: int
    positive_visit_infosets: int
    utility_range: float
    familywise_failure_probability: float
    target_exploitability: float
    probe_iterations: int
    concentration_only_exploitability_at_probe: float
    required_iterations_for_target_concentration_only: int
    maximum_visit_probability: float
    minimum_positive_visit_probability: float
    mean_positive_visit_probability: float
    authority: str = AUTHORITY
    production_certification_eligible: bool = False
    real_routes_certified: int = 0


def concentration_only_exploitability(
    game: HUTwoRoundSubgame,
    profile: StrategyProfile,
    *,
    iterations: int,
    utility_range: float,
    familywise_failure_probability: float,
) -> float:
    alpha = float(familywise_failure_probability)
    if not 0.0 < alpha < 1.0:
        raise ValueError("familywise failure probability must be in (0,1)")
    coordinates = sum(len(actions) for actions in game.info_actions.values())
    if coordinates <= 0:
        raise RuntimeError("visit-weighted Freedman found no action coordinates")
    log_term = math.log(float(coordinates) / alpha)
    total_radius = 0.0
    for traverser in (0, 1):
        visits = external_sampling_infoset_visit_probabilities(game, profile, traverser)
        total_radius += sum(
            _radius(
                iterations=iterations,
                visit_probability=probability,
                utility_range=utility_range,
                log_union_term=log_term,
            )
            for probability in visits.values()
        )
    return 0.5 * total_radius / float(iterations)


def required_iterations_for_target(
    game: HUTwoRoundSubgame,
    profile: StrategyProfile,
    *,
    utility_range: float,
    familywise_failure_probability: float,
    target_exploitability: float,
) -> int:
    target = float(target_exploitability)
    if target <= 0.0 or not math.isfinite(target):
        raise ValueError("target exploitability must be finite and positive")

    def passes(iterations: int) -> bool:
        return concentration_only_exploitability(
            game,
            profile,
            iterations=iterations,
            utility_range=utility_range,
            familywise_failure_probability=familywise_failure_probability,
        ) <= target

    hi = 1
    while not passes(hi):
        hi *= 2
        if hi > 10**30:
            raise RuntimeError("visit-weighted Freedman search exceeded 1e30 iterations")
    lo = 1
    while lo < hi:
        mid = (lo + hi) // 2
        if passes(mid):
            hi = mid
        else:
            lo = mid + 1
    return lo


def evaluate_profile(
    family_id: str,
    profile_id: str,
    game: HUTwoRoundSubgame,
    profile: StrategyProfile,
    *,
    utility_range: float,
    familywise_failure_probability: float,
    target_exploitability: float,
    probe_iterations: int,
) -> VisitWeightedFreedmanResult:
    visits = []
    for traverser in (0, 1):
        visits.extend(
            external_sampling_infoset_visit_probabilities(game, profile, traverser).values()
        )
    positive = [float(p) for p in visits if p > 0.0]
    if not positive:
        raise RuntimeError("visit-weighted Freedman found no positive visits")
    return VisitWeightedFreedmanResult(
        family_id=str(family_id),
        profile_id=str(profile_id),
        infosets=len(visits),
        action_coordinates=sum(len(actions) for actions in game.info_actions.values()),
        positive_visit_infosets=len(positive),
        utility_range=float(utility_range),
        familywise_failure_probability=float(familywise_failure_probability),
        target_exploitability=float(target_exploitability),
        probe_iterations=int(probe_iterations),
        concentration_only_exploitability_at_probe=concentration_only_exploitability(
            game,
            profile,
            iterations=probe_iterations,
            utility_range=utility_range,
            familywise_failure_probability=familywise_failure_probability,
        ),
        required_iterations_for_target_concentration_only=required_iterations_for_target(
            game,
            profile,
            utility_range=utility_range,
            familywise_failure_probability=familywise_failure_probability,
            target_exploitability=target_exploitability,
        ),
        maximum_visit_probability=max(positive),
        minimum_positive_visit_probability=min(positive),
        mean_positive_visit_probability=sum(positive) / float(len(positive)),
    )
