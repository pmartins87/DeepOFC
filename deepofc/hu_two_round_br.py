from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .actions import NormalPlacementAction
from .hu_two_round import (
    HUTwoRoundSubgame,
    StrategyProfile,
    TwoRoundInfoSet,
)


@dataclass(frozen=True)
class TwoRoundBestResponse:
    player: int
    value: float
    choices: Mapping[TwoRoundInfoSet, NormalPlacementAction]


def exact_best_response(
    game: HUTwoRoundSubgame,
    profile: StrategyProfile,
    player: int,
) -> TwoRoundBestResponse:
    """Compute an exact pure best response in the two-round perfect-recall game.

    This deliberately does NOT reuse the one-decision shortcut from hu_subgame.
    The responding player acts once on round 3 and again on round 4. Round-4
    information sets encode the player's exact own round-3 action, including its
    hidden discard, so backward induction can first optimize every round-4
    information set and then propagate those counterfactual values to the
    predecessor round-3 action.

    Counterfactual weights contain chance and every opponent action probability,
    but never the responding player's own strategy probability. Thus every own
    legal action is evaluated even if the supplied profile assigns it zero mass.
    """

    if player not in (0, 1):
        raise ValueError("player must be 0 or 1")

    cp = game.chance_probability
    round4_values: dict[
        TwoRoundInfoSet, dict[NormalPlacementAction, float]
    ] = {}
    round4_parent: dict[
        TwoRoundInfoSet, tuple[TwoRoundInfoSet, NormalPlacementAction]
    ] = {}

    for outcome in game.outcomes:
        first = outcome.first_player
        second = outcome.second_player
        first_r3_info = game.round3_first_info(outcome)
        first_r3_actions = game.actions(first_r3_info)
        first_r3_dist = (
            game._distribution(profile, first_r3_info)
            if first != player
            else None
        )

        for first_r3 in first_r3_actions:
            p_first_r3 = (
                first_r3_dist[first_r3]
                if first_r3_dist is not None
                else 1.0
            )
            second_r3_info = game.round3_second_info(outcome, first_r3)
            second_r3_actions = game.actions(second_r3_info)
            second_r3_dist = (
                game._distribution(profile, second_r3_info)
                if second != player
                else None
            )

            for second_r3 in second_r3_actions:
                p_second_r3 = (
                    second_r3_dist[second_r3]
                    if second_r3_dist is not None
                    else 1.0
                )
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
                first_r4_actions = game.actions(first_r4_info)
                first_r4_dist = (
                    game._distribution(profile, first_r4_info)
                    if first != player
                    else None
                )

                # The BR player's round-3 predecessor is already determined by
                # role and the exact own round-3 action. Perfect recall requires
                # every reached round-4 infoset to map to that same predecessor.
                br_r3_info = (
                    first_r3_info if player == first else second_r3_info
                )
                br_own_r3 = (
                    first_own_r3 if player == first else second_own_r3
                )

                for first_r4 in first_r4_actions:
                    p_first_r4 = (
                        first_r4_dist[first_r4]
                        if first_r4_dist is not None
                        else 1.0
                    )
                    second_r4_info = game.round4_info(
                        outcome,
                        player=second,
                        own_round3_action=second_own_r3,
                        opponent_round3_action=second_opp_r3,
                        current_first_action=first_r4,
                    )
                    second_r4_actions = game.actions(second_r4_info)
                    second_r4_dist = (
                        game._distribution(profile, second_r4_info)
                        if second != player
                        else None
                    )

                    br_r4_info = (
                        first_r4_info if player == first else second_r4_info
                    )
                    parent = (br_r3_info, br_own_r3)
                    previous_parent = round4_parent.setdefault(br_r4_info, parent)
                    if previous_parent != parent:
                        raise AssertionError(
                            "perfect-recall violation: one round-4 infoset maps "
                            "to multiple own round-3 predecessors"
                        )
                    bucket = round4_values.setdefault(
                        br_r4_info,
                        {action: 0.0 for action in game.actions(br_r4_info)},
                    )

                    for second_r4 in second_r4_actions:
                        p_second_r4 = (
                            second_r4_dist[second_r4]
                            if second_r4_dist is not None
                            else 1.0
                        )
                        own_r4 = (
                            first_r4 if player == first else second_r4
                        )
                        u0 = float(
                            game.terminal_u0(
                                outcome,
                                first_r3,
                                second_r3,
                                first_r4,
                                second_r4,
                            )
                        )
                        own_utility = u0 if player == 0 else -u0
                        opponent_reach = (
                            cp
                            * p_first_r3
                            * p_second_r3
                            * p_first_r4
                            * p_second_r4
                        )
                        bucket[own_r4] += opponent_reach * own_utility

    round4_choices: dict[TwoRoundInfoSet, NormalPlacementAction] = {}
    round3_action_values: dict[
        TwoRoundInfoSet, dict[NormalPlacementAction, float]
    ] = {}

    for info, values in round4_values.items():
        best_action = min(
            values,
            key=lambda action: (-values[action], action.key()),
        )
        round4_choices[info] = best_action
        parent_info, parent_action = round4_parent[info]
        parent_bucket = round3_action_values.setdefault(
            parent_info,
            {action: 0.0 for action in game.actions(parent_info)},
        )
        parent_bucket[parent_action] += values[best_action]

    round3_choices: dict[TwoRoundInfoSet, NormalPlacementAction] = {}
    total_value = 0.0
    for info, values in round3_action_values.items():
        best_action = min(
            values,
            key=lambda action: (-values[action], action.key()),
        )
        round3_choices[info] = best_action
        total_value += values[best_action]

    # Every responding-player infoset must receive a pure choice. Missing an
    # infoset would mean the backward aggregation silently dropped a reachable
    # information state or a zero-probability opponent branch.
    expected_infos = {
        info for info in game.info_actions if info.player == player
    }
    choices = {**round3_choices, **round4_choices}
    if set(choices) != expected_infos:
        missing = expected_infos - set(choices)
        extra = set(choices) - expected_infos
        raise AssertionError(
            f"best response infoset coverage mismatch: missing={len(missing)} extra={len(extra)}"
        )

    return TwoRoundBestResponse(
        player=player,
        value=total_value,
        choices=choices,
    )


def profile_with_pure_response(
    game: HUTwoRoundSubgame,
    opponent_profile: StrategyProfile,
    response: TwoRoundBestResponse,
) -> dict[TwoRoundInfoSet, dict[NormalPlacementAction, float]]:
    """Materialize a full profile for independent expected-value cross-checking."""

    merged: dict[TwoRoundInfoSet, dict[NormalPlacementAction, float]] = {}
    for info, actions in game.info_actions.items():
        if info.player == response.player:
            chosen = response.choices[info]
            merged[info] = {
                action: 1.0 if action == chosen else 0.0
                for action in actions
            }
        else:
            merged[info] = game._distribution(opponent_profile, info)
    return merged


def exact_nash_conv(
    game: HUTwoRoundSubgame,
    profile: StrategyProfile,
) -> tuple[float, TwoRoundBestResponse, TwoRoundBestResponse]:
    br0 = exact_best_response(game, profile, 0)
    br1 = exact_best_response(game, profile, 1)
    return br0.value + br1.value, br0, br1
