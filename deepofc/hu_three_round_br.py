from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .actions import NormalPlacementAction
from .hu_three_round_sequential import (
    HUThreeRoundSequentialSubgame,
    StrategyProfile,
)
from .sequential import HUPlayerObservation, HUSequentialNormalState


@dataclass(frozen=True)
class ThreeRoundBestResponse:
    player: int
    value: float
    choices: Mapping[HUPlayerObservation, NormalPlacementAction]
    terminal_histories: int


def _best_action(
    values: Mapping[NormalPlacementAction, float],
) -> NormalPlacementAction:
    return min(values, key=lambda action: (-values[action], action.key()))


def exact_best_response(
    game: HUThreeRoundSequentialSubgame,
    profile: StrategyProfile,
    player: int,
) -> ThreeRoundBestResponse:
    """Exact pure BR for the three-decision perfect-recall HU benchmark.

    The responding player's own behavioral probabilities are never multiplied
    into counterfactual reach. Chance probability and every opponent action
    probability are included. Terminal utilities are first accumulated at the
    responding player's deepest (round-4) infoset/action and then propagated
    backward through the unique own perfect-recall predecessor chain:

        round 4 -> round 3 -> round 2.

    This is the direct three-level generalization of the independently audited
    two-round best-response construction.
    """

    if player not in (0, 1):
        raise ValueError("player must be 0 or 1")

    values_by_depth: dict[
        int,
        dict[HUPlayerObservation, dict[NormalPlacementAction, float]],
    ] = {0: {}, 1: {}, 2: {}}
    parent: dict[
        HUPlayerObservation,
        tuple[HUPlayerObservation, NormalPlacementAction],
    ] = {}
    expected_infos: set[HUPlayerObservation] = set()
    terminal_histories = 0

    def bucket_for(
        depth: int, info: HUPlayerObservation
    ) -> dict[NormalPlacementAction, float]:
        return values_by_depth[depth].setdefault(
            info,
            {action: 0.0 for action in game.actions(info)},
        )

    def recurse(
        state: HUSequentialNormalState,
        opponent_reach: float,
        own_sequence: tuple[
            tuple[HUPlayerObservation, NormalPlacementAction], ...
        ],
    ) -> None:
        nonlocal terminal_histories
        if state.terminal:
            terminal_histories += 1
            if len(own_sequence) != 3:
                raise AssertionError(
                    f"responding player must act exactly three times, got {len(own_sequence)}"
                )
            info, action = own_sequence[-1]
            u0 = float(game.terminal_u0(state))
            own_utility = u0 if player == 0 else -u0
            bucket_for(2, info)[action] += opponent_reach * own_utility
            return

        info = game.info(state)
        actor = state.acting_chair
        legal = game.actions(info)
        if actor == player:
            expected_infos.add(info)
            depth = info.state.round_index - 2
            if depth not in (0, 1, 2):
                raise AssertionError(f"unexpected BR decision depth: {depth}")
            if len(own_sequence) != depth:
                raise AssertionError(
                    "perfect-recall decision-depth mismatch: "
                    f"round={info.state.round_index} prior_own={len(own_sequence)}"
                )
            # Create the bucket even before terminal propagation so zero-weight
            # opponent branches remain covered and receive deterministic choices.
            bucket_for(depth, info)
            if depth > 0:
                predecessor = own_sequence[-1]
                previous = parent.setdefault(info, predecessor)
                if previous != predecessor:
                    raise AssertionError(
                        "perfect-recall violation: one infoset has multiple own predecessors"
                    )
            for action in legal:
                recurse(
                    state.apply(action),
                    opponent_reach,
                    (*own_sequence, (info, action)),
                )
            return

        distribution = game.distribution(profile, info)
        # Traverse zero-probability opponent actions as well. They contribute
        # zero counterfactual mass but are required to prove BR infoset coverage
        # on off-profile branches.
        for action in legal:
            recurse(
                state.apply(action),
                opponent_reach * distribution[action],
                own_sequence,
            )

    for outcome in game.outcomes:
        recurse(
            game.initial_state(outcome),
            game.chance_probability,
            (),
        )

    choices: dict[HUPlayerObservation, NormalPlacementAction] = {}
    total_value = 0.0
    for depth in (2, 1, 0):
        for info, values in values_by_depth[depth].items():
            chosen = _best_action(values)
            choices[info] = chosen
            best_value = values[chosen]
            if depth == 0:
                total_value += best_value
            else:
                parent_info, parent_action = parent[info]
                parent_bucket = bucket_for(depth - 1, parent_info)
                parent_bucket[parent_action] += best_value

    if set(choices) != expected_infos:
        missing = expected_infos - set(choices)
        extra = set(choices) - expected_infos
        raise AssertionError(
            f"three-round BR infoset coverage mismatch: missing={len(missing)} extra={len(extra)}"
        )

    return ThreeRoundBestResponse(
        player=player,
        value=total_value,
        choices=choices,
        terminal_histories=terminal_histories,
    )


def profile_with_pure_response(
    game: HUThreeRoundSequentialSubgame,
    opponent_profile: StrategyProfile,
    response: ThreeRoundBestResponse,
) -> dict[HUPlayerObservation, dict[NormalPlacementAction, float]]:
    """Sparse full-profile overlay for independent expected-value replay.

    Opponent entries explicitly supplied in `opponent_profile` are preserved;
    missing opponent infosets continue to use the game's uniform fallback.
    Every responding-player infoset discovered by the exact BR is overwritten by
    the corresponding deterministic one-hot action.
    """

    merged = {
        info: {action: float(probability) for action, probability in dist.items()}
        for info, dist in opponent_profile.items()
    }
    for info, chosen in response.choices.items():
        merged[info] = {
            action: 1.0 if action == chosen else 0.0
            for action in game.actions(info)
        }
    return merged


def exact_nash_conv(
    game: HUThreeRoundSequentialSubgame,
    profile: StrategyProfile,
) -> tuple[float, ThreeRoundBestResponse, ThreeRoundBestResponse]:
    br0 = exact_best_response(game, profile, 0)
    br1 = exact_best_response(game, profile, 1)
    return br0.value + br1.value, br0, br1
