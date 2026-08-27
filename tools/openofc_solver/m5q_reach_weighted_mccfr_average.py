from __future__ import annotations

"""Exact reduced-game CFR-average semantics layered on External Sampling MCCFR.

This candidate deliberately does not change sampled-regret training semantics.
Before each sampled MCCFR update it records the current strategy with the same
own-reach/chance weighting used by the full-tree CFR reference implementation.
The implementation enumerates the reduced-game public/chance surface exactly,
so it is a validation/reference mechanism rather than a scalable full-game
averaging implementation.
"""

from dataclasses import dataclass
from typing import Mapping

from deepofc.actions import NormalPlacementAction
from deepofc.hu_two_round import HUTwoRoundSubgame, StrategyProfile, TwoRoundInfoSet
from deepofc.hu_two_round_mccfr import TwoRoundExternalSamplingMCCFR

AUTHORITY = "EXACT_REDUCED_GAME_REACH_WEIGHTED_CFR_AVERAGE_REFERENCE_NOT_CERTIFICATION"

AverageTable = dict[TwoRoundInfoSet, dict[NormalPlacementAction, float]]


def _empty_table(game: HUTwoRoundSubgame) -> AverageTable:
    return {
        info: {action: 0.0 for action in actions}
        for info, actions in game.info_actions.items()
    }


def _add_strategy(
    target: AverageTable,
    info: TwoRoundInfoSet,
    distribution: Mapping[NormalPlacementAction, float],
    reach_weight: float,
) -> None:
    bucket = target[info]
    for action, probability in distribution.items():
        bucket[action] += float(reach_weight) * float(probability)


def exact_reference_average_delta(
    game: HUTwoRoundSubgame,
    profile: StrategyProfile,
) -> AverageTable:
    """Return one standard-CFR average-strategy increment for ``profile``.

    The traversal is intentionally isomorphic to the average-strategy portion
    of ``TwoRoundFullTreeCFR.step``.  Chance reach is retained exactly as in
    that frozen reference.  Opponent reach is excluded; a player's own earlier
    action reach is included at its later decision, which is the key semantic
    difference from a local behavioral time average.
    """

    delta = _empty_table(game)
    cp = float(game.chance_probability)
    for outcome in game.outcomes:
        first = outcome.first_player
        second = outcome.second_player

        first_r3_info = game.round3_first_info(outcome)
        first_r3_dist = profile[first_r3_info]
        _add_strategy(delta, first_r3_info, first_r3_dist, cp)

        for first_r3, p_first_r3 in first_r3_dist.items():
            second_r3_info = game.round3_second_info(outcome, first_r3)
            second_r3_dist = profile[second_r3_info]
            _add_strategy(delta, second_r3_info, second_r3_dist, cp)

            for second_r3, p_second_r3 in second_r3_dist.items():
                _, _, action0_r3, action1_r3 = game._boards_after_round3(
                    outcome, first_r3, second_r3
                )
                first_own_r3 = action0_r3 if first == 0 else action1_r3
                first_opp_r3 = action1_r3 if first == 0 else action0_r3
                second_own_r3 = action0_r3 if second == 0 else action1_r3
                second_opp_r3 = action1_r3 if second == 0 else action0_r3

                first_r4_info = game.round4_info(
                    outcome,
                    player=first,
                    own_round3_action=first_own_r3,
                    opponent_round3_action=first_opp_r3,
                    current_first_action=None,
                )
                first_r4_dist = profile[first_r4_info]
                _add_strategy(
                    delta,
                    first_r4_info,
                    first_r4_dist,
                    cp * float(p_first_r3),
                )

                for first_r4 in first_r4_dist:
                    second_r4_info = game.round4_info(
                        outcome,
                        player=second,
                        own_round3_action=second_own_r3,
                        opponent_round3_action=second_opp_r3,
                        current_first_action=first_r4,
                    )
                    second_r4_dist = profile[second_r4_info]
                    _add_strategy(
                        delta,
                        second_r4_info,
                        second_r4_dist,
                        cp * float(p_second_r3),
                    )
    return delta


def _normalized_profile(game: HUTwoRoundSubgame, table: AverageTable) -> StrategyProfile:
    profile: StrategyProfile = {}
    for info, actions in game.info_actions.items():
        totals = table[info]
        mass = sum(totals.values())
        if mass <= 0.0:
            probability = 1.0 / len(actions)
            profile[info] = {action: probability for action in actions}
        else:
            profile[info] = {
                action: float(totals[action]) / float(mass)
                for action in actions
            }
    return profile


@dataclass(frozen=True)
class ReachWeightedAverageStatus:
    recorded_iterations: int
    authority: str = AUTHORITY
    production_certification_eligible: bool = False
    real_routes_certified: int = 0


class ReachWeightedAverageExternalSamplingMCCFR(TwoRoundExternalSamplingMCCFR):
    """External Sampling MCCFR with exact reduced-game CFR-average recording.

    ``super().step()`` remains the sole regret/training update.  The extra work
    is deterministic and consumes no RNG, making the sampled-regret trajectory
    identical to the uninstrumented solver for the same seed.
    """

    average_authority = AUTHORITY

    def __init__(self, game: HUTwoRoundSubgame, *, seed: int = 1) -> None:
        super().__init__(game, seed=seed)
        self.reach_weighted_strategy_sum = _empty_table(game)
        self.reach_weighted_recorded_iterations = 0

    def record_current_profile_for_reach_weighted_average(self) -> None:
        current = self.current_profile()
        delta = exact_reference_average_delta(self.game, current)
        for info, values in delta.items():
            totals = self.reach_weighted_strategy_sum[info]
            for action, increment in values.items():
                totals[action] += increment
        self.reach_weighted_recorded_iterations += 1

    def step(self) -> None:
        self.record_current_profile_for_reach_weighted_average()
        super().step()

    def reach_weighted_average_profile(self) -> StrategyProfile:
        return _normalized_profile(self.game, self.reach_weighted_strategy_sum)

    def reach_weighted_average_status(self) -> ReachWeightedAverageStatus:
        return ReachWeightedAverageStatus(
            recorded_iterations=self.reach_weighted_recorded_iterations
        )
