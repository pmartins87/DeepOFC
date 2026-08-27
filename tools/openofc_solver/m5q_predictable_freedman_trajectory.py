from __future__ import annotations

"""Adaptive reduced-game External Sampling with predictable-visit PQV accounting.

The training update is inherited unchanged from the production reduced-game
External Sampling kernel. Before each update, this reference computes the exact
conditional visit probability of every traverser infoset under the current
pre-update strategy and accumulates it as a predictable variance envelope.

No RNG is consumed by the instrumentation. This module is a reduced-game
research/certification reference, not a production solver and not a route
certificate.
"""

from dataclasses import dataclass
import math

from deepofc.hu_two_round import HUTwoRoundSubgame, TwoRoundInfoSet
from deepofc.hu_two_round_mccfr import TwoRoundExternalSamplingMCCFR
from m5q_predictable_visit_variance import external_sampling_infoset_visit_probabilities

AUTHORITY = "ADAPTIVE_PREDICTABLE_VISIT_FREEDMAN_REFERENCE_NOT_CERTIFICATION"


@dataclass(frozen=True)
class PredictableFreedmanRegretBound:
    iterations: int
    familywise_failure_probability: float
    utility_range: float
    action_coordinates: int
    player0_sampled_positive_regret: float
    player1_sampled_positive_regret: float
    sampled_positive_regret_exploitability: float
    player0_freedman_regret_upper: float
    player1_freedman_regret_upper: float
    nash_conv_upper: float
    exploitability_upper: float
    concentration_additive_exploitability: float
    maximum_coordinate_predictable_variation: float
    total_coordinate_predictable_variation: float
    authority: str = AUTHORITY
    production_certification_eligible: bool = False
    real_routes_certified: int = 0


def _freedman_radius(*, predictable_variation: float, increment_upper: float, log_term: float) -> float:
    variance = float(predictable_variation)
    r = float(increment_upper)
    if variance < 0.0 or not math.isfinite(variance):
        raise ValueError("predictable variation must be finite and nonnegative")
    if variance == 0.0:
        return 0.0
    if r <= 0.0 or not math.isfinite(r) or log_term <= 0.0 or not math.isfinite(log_term):
        raise ValueError("Freedman constants must be finite and positive")
    linear = r * log_term / 3.0
    return linear + math.sqrt(linear * linear + 2.0 * variance * log_term)


class PredictableVarianceExternalSamplingMCCFR(TwoRoundExternalSamplingMCCFR):
    authority = AUTHORITY

    def __init__(self, game: HUTwoRoundSubgame, *, seed: int = 1) -> None:
        super().__init__(game, seed=seed)
        self.predictable_visit_sum: dict[TwoRoundInfoSet, float] = {
            info: 0.0 for info in game.info_actions
        }
        self.predictable_accounted_iterations = 0

    def record_predictable_visits(self) -> None:
        profile = self.current_profile()
        for traverser in (0, 1):
            visits = external_sampling_infoset_visit_probabilities(
                self.game, profile, traverser
            )
            for info, probability in visits.items():
                self.predictable_visit_sum[info] += float(probability)
        self.predictable_accounted_iterations += 1

    def step(self) -> None:
        self.record_predictable_visits()
        super().step()
        if self.predictable_accounted_iterations != self.iteration:
            raise AssertionError("predictable visit accounting lost MCCFR iteration alignment")

    def regret_bound(
        self,
        *,
        utility_range: float,
        familywise_failure_probability: float = 0.05,
    ) -> PredictableFreedmanRegretBound:
        if self.iteration <= 0:
            raise ValueError("regret bound requires at least one completed iteration")
        if self.predictable_accounted_iterations != self.iteration:
            raise RuntimeError("predictable visit accounting is not aligned with training")
        delta = float(utility_range)
        alpha = float(familywise_failure_probability)
        if delta <= 0.0 or not math.isfinite(delta):
            raise ValueError("utility range must be finite and positive")
        if not 0.0 < alpha < 1.0:
            raise ValueError("familywise failure probability must be in (0,1)")
        coordinates = sum(len(actions) for actions in self.game.info_actions.values())
        log_term = math.log(float(coordinates) / alpha)
        increment_upper = 2.0 * delta
        delta2 = delta * delta

        sampled_positive = [0.0, 0.0]
        bounded_regret = [0.0, 0.0]
        max_variation = 0.0
        total_coordinate_variation = 0.0

        for info, actions in self.game.info_actions.items():
            sampled_max = max(float(self.regrets[info][action]) for action in actions)
            sampled_positive[info.player] += max(0.0, sampled_max)
            variation = self.predictable_visit_sum[info] * delta2
            max_variation = max(max_variation, variation)
            total_coordinate_variation += variation * float(len(actions))
            radius = _freedman_radius(
                predictable_variation=variation,
                increment_upper=increment_upper,
                log_term=log_term,
            )
            bounded_regret[info.player] += max(0.0, sampled_max + radius)

        iterations = float(self.iteration)
        sampled_exploitability = 0.5 * sum(sampled_positive) / iterations
        nash_conv_upper = sum(bounded_regret) / iterations
        exploitability_upper = 0.5 * nash_conv_upper
        return PredictableFreedmanRegretBound(
            iterations=self.iteration,
            familywise_failure_probability=alpha,
            utility_range=delta,
            action_coordinates=coordinates,
            player0_sampled_positive_regret=sampled_positive[0],
            player1_sampled_positive_regret=sampled_positive[1],
            sampled_positive_regret_exploitability=sampled_exploitability,
            player0_freedman_regret_upper=bounded_regret[0],
            player1_freedman_regret_upper=bounded_regret[1],
            nash_conv_upper=nash_conv_upper,
            exploitability_upper=exploitability_upper,
            concentration_additive_exploitability=max(
                0.0, exploitability_upper - sampled_exploitability
            ),
            maximum_coordinate_predictable_variation=max_variation,
            total_coordinate_predictable_variation=total_coordinate_variation,
        )
