from __future__ import annotations

"""Exact reduced-game predictable visitation probabilities for External Sampling.

For a traverser, own actions are enumerated while chance and opponent actions are
sampled.  A regret coordinate at infoset I is therefore updated only when I is
visited by that sampled traversal.  If every coordinate update is bounded by
Delta_u, then

    E[X_t(I,a)^2 | F_{t-1}] <= P_t(visit I | F_{t-1}) * Delta_u^2.

This module computes that visit probability exactly for the frozen two-round
reduced-game structure.  It is a variance-accounting reference, not a strategic
certificate and not yet a scalable full-game implementation.
"""

from dataclasses import dataclass
import math
from typing import Mapping

from deepofc.actions import NormalPlacementAction
from deepofc.hu_two_round import HUTwoRoundSubgame, StrategyProfile, TwoRoundInfoSet

AUTHORITY = "EXACT_REDUCED_GAME_EXTERNAL_SAMPLING_VISIT_VARIANCE_REFERENCE_NOT_CERTIFICATION"


def external_sampling_infoset_visit_probabilities(
    game: HUTwoRoundSubgame,
    profile: StrategyProfile,
    traverser: int,
) -> dict[TwoRoundInfoSet, float]:
    """Return exact conditional visit probability for every traverser infoset."""

    if traverser not in (0, 1):
        raise ValueError("traverser must be 0 or 1")
    visits = {
        info: 0.0
        for info in game.info_actions
        if info.player == traverser
    }
    cp = float(game.chance_probability)
    if not math.isfinite(cp) or cp <= 0.0:
        raise ValueError("chance probability must be finite and positive")

    for outcome in game.outcomes:
        first = outcome.first_player
        second = outcome.second_player
        first_r3_info = game.round3_first_info(outcome)
        first_r3_dist = game._distribution(profile, first_r3_info)

        if traverser == first:
            visits[first_r3_info] += cp
            # Own r3 actions are enumerated.  The second player's r3 action is
            # sampled independently on each own-action branch.
            for first_r3 in game.actions(first_r3_info):
                second_r3_info = game.round3_second_info(outcome, first_r3)
                second_r3_dist = game._distribution(profile, second_r3_info)
                for second_r3, p_second_r3 in second_r3_dist.items():
                    board0, board1, action0_r3, action1_r3 = game._boards_after_round3(
                        outcome, first_r3, second_r3
                    )
                    first_own_r3 = action0_r3 if first == 0 else action1_r3
                    first_opp_r3 = action1_r3 if first == 0 else action0_r3
                    first_r4_info = game.round4_info(
                        outcome,
                        player=first,
                        own_round3_action=first_own_r3,
                        opponent_round3_action=first_opp_r3,
                        current_first_action=None,
                    )
                    visits[first_r4_info] += cp * float(p_second_r3)
            continue

        if traverser != second:
            raise AssertionError("two-player outcome has invalid traverser identity")

        # First r3 is an opponent sample before the traverser's second-actor r3
        # infoset is reached.
        for first_r3, p_first_r3 in first_r3_dist.items():
            second_r3_info = game.round3_second_info(outcome, first_r3)
            visits[second_r3_info] += cp * float(p_first_r3)
            # Traverser's own r3 actions are enumerated.  On each branch the
            # opponent's r4 action is sampled before the traverser's r4 infoset.
            for second_r3 in game.actions(second_r3_info):
                board0, board1, action0_r3, action1_r3 = game._boards_after_round3(
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
                first_r4_dist = game._distribution(profile, first_r4_info)
                for first_r4, p_first_r4 in first_r4_dist.items():
                    second_r4_info = game.round4_info(
                        outcome,
                        player=second,
                        own_round3_action=second_own_r3,
                        opponent_round3_action=second_opp_r3,
                        current_first_action=first_r4,
                    )
                    visits[second_r4_info] += (
                        cp * float(p_first_r3) * float(p_first_r4)
                    )

    for info, probability in visits.items():
        if not math.isfinite(probability) or probability < -1e-15:
            raise FloatingPointError(f"invalid visit probability for {info!r}: {probability}")
        if probability > 1.0 + 1e-12:
            # One infoset can be updated at most once in one traverser traversal
            # on this frozen perfect-recall two-round surface.
            raise AssertionError(
                f"infoset visit probability exceeds one: {info!r} -> {probability}"
            )
        visits[info] = max(0.0, min(1.0, float(probability)))
    return visits


def expected_round4_visits_per_traversal(
    game: HUTwoRoundSubgame,
    traverser: int,
) -> float:
    """Exact expected count of traverser round-4 infosets visited per traversal."""
    if traverser not in (0, 1):
        raise ValueError("traverser must be 0 or 1")
    cp = float(game.chance_probability)
    return sum(
        cp * float(len(game._round3_actions(outcome, traverser)))
        for outcome in game.outcomes
    )


@dataclass(frozen=True)
class PredictableVisitVarianceSummary:
    traverser: int
    infosets: int
    round3_visit_mass: float
    round4_visit_mass: float
    expected_round4_visit_mass: float
    minimum_positive_visit_probability: float
    maximum_visit_probability: float
    mean_visit_probability: float
    utility_range: float
    maximum_coordinate_conditional_second_moment_bound: float
    total_coordinate_conditional_second_moment_bound: float
    authority: str = AUTHORITY
    production_certification_eligible: bool = False
    real_routes_certified: int = 0


def predictable_visit_variance_summary(
    game: HUTwoRoundSubgame,
    profile: StrategyProfile,
    traverser: int,
    *,
    utility_range: float,
) -> PredictableVisitVarianceSummary:
    delta = float(utility_range)
    if not math.isfinite(delta) or delta <= 0.0:
        raise ValueError("utility_range must be finite and positive")
    visits = external_sampling_infoset_visit_probabilities(game, profile, traverser)
    positives = [p for p in visits.values() if p > 0.0]
    if not positives:
        raise RuntimeError("predictable visit audit found no reachable traverser infosets")
    r3 = sum(p for info, p in visits.items() if info.round_index == 3)
    r4 = sum(p for info, p in visits.items() if info.round_index == 4)
    expected_r4 = expected_round4_visits_per_traversal(game, traverser)
    if abs(r3 - 1.0) > 1e-10:
        raise AssertionError(f"round-3 visit mass must equal one, got {r3}")
    if abs(r4 - expected_r4) > 1e-10:
        raise AssertionError(
            f"round-4 visit mass mismatch: observed={r4} expected={expected_r4}"
        )
    delta2 = delta * delta
    total_coordinate_second = sum(
        probability * delta2 * len(game.actions(info))
        for info, probability in visits.items()
    )
    return PredictableVisitVarianceSummary(
        traverser=traverser,
        infosets=len(visits),
        round3_visit_mass=r3,
        round4_visit_mass=r4,
        expected_round4_visit_mass=expected_r4,
        minimum_positive_visit_probability=min(positives),
        maximum_visit_probability=max(positives),
        mean_visit_probability=sum(visits.values()) / float(len(visits)),
        utility_range=delta,
        maximum_coordinate_conditional_second_moment_bound=max(positives) * delta2,
        total_coordinate_conditional_second_moment_bound=total_coordinate_second,
    )
