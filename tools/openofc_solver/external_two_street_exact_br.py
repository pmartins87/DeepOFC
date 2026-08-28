from __future__ import annotations

"""Exact pure best response for the frozen finite-support R3->R4 game.

Authority:
  EXACT_FINITE_SUPPORT_TWO_STREET_BR_REDUCED_GAME_ONLY
"""

from dataclasses import dataclass
import math
from typing import Iterable, Mapping, Sequence

from external_two_street_counterfactual_resolve import (
    ReachableInfoSetSupport,
    build_reachable_infoset_support,
    exact_profile_value_strict,
)
from external_two_street_infoset_search import TwoStreetWorld, _assert_root_isolation, _with_world
from external_two_street_mccfr import BehaviorProfile, ExactProfileEvaluation
from strategic_cfr import HUState, child_state, information_state_key, legal_action_pairs, terminal_utility

AUTHORITY = "EXACT_FINITE_SUPPORT_TWO_STREET_BR_REDUCED_GAME_ONLY"
SCHEMA = "openofc-external-two-street-exact-br-v1"
ReadOnlyProfile = Mapping[str, Mapping[str, float]]


@dataclass(frozen=True)
class ExactTwoStreetBestResponse:
    player: int
    value: float
    choices: tuple[tuple[str, str], ...]
    round3_infosets: int
    round4_infosets: int
    terminal_leaves: int

    def choice_map(self) -> dict[str, str]:
        return dict(self.choices)


@dataclass(frozen=True)
class ExactTwoStreetNashConv:
    nash_conv: float
    exploitability: float
    br0: ExactTwoStreetBestResponse
    br1: ExactTwoStreetBestResponse


def _distribution(
    profile: ReadOnlyProfile,
    info_key: str,
    action_keys: Sequence[str],
) -> dict[str, float]:
    legal = tuple(action_keys)
    supplied = profile.get(info_key)
    if supplied is None:
        raise ValueError(f"exact BR requires explicit opponent policy at infoset: {info_key}")
    illegal = set(supplied) - set(legal)
    if illegal:
        raise ValueError(f"profile contains illegal actions at infoset: {sorted(illegal)}")
    weights: dict[str, float] = {}
    for key in legal:
        value = float(supplied.get(key, 0.0))
        if value < 0.0 or not math.isfinite(value):
            raise ValueError("profile probabilities must be finite and non-negative")
        weights[key] = value
    mass = sum(weights.values())
    if mass <= 0.0:
        raise ValueError("exact BR refuses zero-mass opponent policy")
    return {key: value / mass for key, value in weights.items()}


def exact_best_response(
    base_state: HUState,
    worlds: Iterable[TwoStreetWorld],
    *,
    opponent_profile: ReadOnlyProfile,
    player: int,
    support_rows: Sequence[ReachableInfoSetSupport] | None = None,
) -> ExactTwoStreetBestResponse:
    """Compute exact pure BR by counterfactual backward aggregation.

    Chance and opponent behavior contribute to reach. The responding player's
    own behavior never contributes, so every own legal action is evaluated.
    """
    if player not in (0, 1):
        raise ValueError("player must be 0 or 1")
    support = tuple(worlds)
    if len(support) < 2:
        raise ValueError("exact BR requires at least two physical worlds")
    _assert_root_isolation(base_state, support)
    rows = tuple(support_rows) if support_rows is not None else build_reachable_infoset_support(base_state, support)

    expected_opponent_infos = {
        row.information_state_key for row in rows if row.actor != player
    }
    missing_opponent = expected_opponent_infos - set(opponent_profile)
    if missing_opponent:
        raise ValueError(
            f"exact BR opponent profile incomplete: missing={len(missing_opponent)}"
        )

    action_sets: dict[str, tuple[str, ...]] = {}
    actor_round: dict[str, tuple[int, int]] = {}
    round4_values: dict[str, dict[str, float]] = {}
    round4_parent: dict[str, tuple[str, str]] = {}
    terminal_leaves = 0
    chance = 1.0 / len(support)

    def remember_node(state: HUState) -> tuple[str, tuple[tuple[str, object], ...]]:
        info_key = information_state_key(state)
        pairs = tuple(legal_action_pairs(state))
        action_keys = tuple(key for key, _action in pairs)
        previous = action_sets.get(info_key)
        if previous is None:
            action_sets[info_key] = action_keys
            actor_round[info_key] = (state.actor, state.round_index)
        else:
            if previous != action_keys:
                raise AssertionError("same information state produced different legal actions")
            if actor_round[info_key] != (state.actor, state.round_index):
                raise AssertionError("information-state key collided across actor/round")
        return info_key, pairs

    def walk(
        state: HUState,
        opponent_reach: float,
        br_r3_info: str | None,
        br_r3_action: str | None,
        br_r4_info: str | None,
        br_r4_action: str | None,
    ) -> None:
        nonlocal terminal_leaves
        if state.terminal():
            terminal_leaves += 1
            if br_r3_info is None or br_r3_action is None or br_r4_info is None or br_r4_action is None:
                raise AssertionError("terminal BR path is missing one of the responder's two decisions")
            own_utility = float(terminal_utility(state, player))
            bucket = round4_values.setdefault(
                br_r4_info,
                {action_key: 0.0 for action_key in action_sets[br_r4_info]},
            )
            bucket[br_r4_action] += chance * opponent_reach * own_utility
            parent = (br_r3_info, br_r3_action)
            previous_parent = round4_parent.setdefault(br_r4_info, parent)
            if previous_parent != parent:
                raise AssertionError(
                    "perfect-recall violation: one R4 infoset maps to multiple own R3 predecessors"
                )
            return

        info_key, pairs = remember_node(state)
        action_keys = action_sets[info_key]
        by_key = dict(pairs)

        if state.actor == player:
            for action_key in action_keys:
                if state.round_index == 3:
                    if br_r3_info is not None or br_r3_action is not None:
                        raise AssertionError("responder encountered duplicate R3 decision")
                    walk(
                        child_state(state, by_key[action_key]),
                        opponent_reach,
                        info_key,
                        action_key,
                        br_r4_info,
                        br_r4_action,
                    )
                elif state.round_index == 4:
                    if br_r3_info is None or br_r3_action is None:
                        raise AssertionError("responder R4 decision has no R3 predecessor")
                    walk(
                        child_state(state, by_key[action_key]),
                        opponent_reach,
                        br_r3_info,
                        br_r3_action,
                        info_key,
                        action_key,
                    )
                else:
                    raise AssertionError("05E reduced game expects responder decisions only on R3/R4")
            return

        distribution = _distribution(opponent_profile, info_key, action_keys)
        for action_key in action_keys:
            probability = distribution[action_key]
            # Zero-probability opponent branches are still traversed so every
            # responder information state receives a deterministic choice; their
            # contribution to value is exactly zero.
            walk(
                child_state(state, by_key[action_key]),
                opponent_reach * probability,
                br_r3_info,
                br_r3_action,
                br_r4_info,
                br_r4_action,
            )

    for world in support:
        walk(_with_world(base_state, world), 1.0, None, None, None, None)

    expected_own_infos = {
        row.information_state_key for row in rows if row.actor == player
    }
    expected_r3 = {
        row.information_state_key for row in rows if row.actor == player and row.round_index == 3
    }
    expected_r4 = {
        row.information_state_key for row in rows if row.actor == player and row.round_index == 4
    }

    round4_choices: dict[str, str] = {}
    round3_action_values: dict[str, dict[str, float]] = {
        info_key: {action_key: 0.0 for action_key in action_sets.get(info_key, ())}
        for info_key in expected_r3
    }

    for info_key in sorted(expected_r4):
        values = round4_values.get(info_key)
        if values is None:
            # This can only happen if the entire information state has zero
            # opponent/chance reach under the fixed profile. It still receives a
            # deterministic lexicographic choice with zero counterfactual value.
            actions = action_sets.get(info_key)
            if not actions:
                raise AssertionError("reachable R4 infoset was never materialized")
            values = {action_key: 0.0 for action_key in actions}
        best_action = min(values, key=lambda action_key: (-values[action_key], action_key))
        round4_choices[info_key] = best_action
        parent = round4_parent.get(info_key)
        if parent is None:
            # A zero-reach R4 infoset may not have received a terminal
            # contribution. Recover its unique parent by scanning support rows is
            # not possible from the key alone, so zero-reach branches are still
            # deliberately traversed above and should have installed a parent.
            raise AssertionError("R4 infoset missing perfect-recall parent mapping")
        parent_info, parent_action = parent
        parent_bucket = round3_action_values.setdefault(
            parent_info,
            {action_key: 0.0 for action_key in action_sets[parent_info]},
        )
        parent_bucket[parent_action] += values[best_action]

    round3_choices: dict[str, str] = {}
    total_value = 0.0
    for info_key in sorted(expected_r3):
        values = round3_action_values.get(info_key)
        if not values:
            actions = action_sets.get(info_key)
            if not actions:
                raise AssertionError("reachable R3 infoset was never materialized")
            values = {action_key: 0.0 for action_key in actions}
        best_action = min(values, key=lambda action_key: (-values[action_key], action_key))
        round3_choices[info_key] = best_action
        total_value += values[best_action]

    choices = {**round3_choices, **round4_choices}
    if set(choices) != expected_own_infos:
        missing = expected_own_infos - set(choices)
        extra = set(choices) - expected_own_infos
        raise AssertionError(
            f"best-response infoset coverage mismatch: missing={len(missing)} extra={len(extra)}"
        )

    return ExactTwoStreetBestResponse(
        player=player,
        value=total_value,
        choices=tuple(sorted(choices.items())),
        round3_infosets=len(round3_choices),
        round4_infosets=len(round4_choices),
        terminal_leaves=terminal_leaves,
    )


def profile_with_pure_response(
    support_rows: Sequence[ReachableInfoSetSupport],
    *,
    opponent_profile: ReadOnlyProfile,
    response: ExactTwoStreetBestResponse,
) -> BehaviorProfile:
    """Materialize a complete profile for independent replay of the pure BR."""
    choice_map = response.choice_map()
    merged: BehaviorProfile = {}
    for row in support_rows:
        if row.actor == response.player:
            chosen = choice_map[row.information_state_key]
            merged[row.information_state_key] = {
                action_key: 1.0 if action_key == chosen else 0.0
                for action_key in row.action_keys
            }
        else:
            merged[row.information_state_key] = _distribution(
                opponent_profile,
                row.information_state_key,
                row.action_keys,
            )
    return merged


def replay_best_response_value(
    base_state: HUState,
    worlds: Iterable[TwoStreetWorld],
    *,
    support_rows: Sequence[ReachableInfoSetSupport],
    opponent_profile: ReadOnlyProfile,
    response: ExactTwoStreetBestResponse,
) -> ExactProfileEvaluation:
    profile = profile_with_pure_response(
        support_rows,
        opponent_profile=opponent_profile,
        response=response,
    )
    result = exact_profile_value_strict(
        base_state,
        worlds,
        support_rows=support_rows,
        p0_profile=profile,
        p1_profile=profile,
    )
    expected_own = result.expected_u0 if response.player == 0 else -result.expected_u0
    if not math.isclose(expected_own, response.value, rel_tol=1e-10, abs_tol=1e-10):
        raise AssertionError(
            f"direct BR value disagrees with independent replay: direct={response.value} replay={expected_own}"
        )
    return result


def exact_nash_conv(
    base_state: HUState,
    worlds: Iterable[TwoStreetWorld],
    *,
    profile: ReadOnlyProfile,
    support_rows: Sequence[ReachableInfoSetSupport] | None = None,
) -> ExactTwoStreetNashConv:
    support = tuple(worlds)
    rows = tuple(support_rows) if support_rows is not None else build_reachable_infoset_support(base_state, support)
    br0 = exact_best_response(
        base_state,
        support,
        opponent_profile=profile,
        player=0,
        support_rows=rows,
    )
    br1 = exact_best_response(
        base_state,
        support,
        opponent_profile=profile,
        player=1,
        support_rows=rows,
    )
    nash_conv = br0.value + br1.value
    if nash_conv < -1e-9:
        raise AssertionError(f"zero-sum NashConv became negative: {nash_conv}")
    return ExactTwoStreetNashConv(
        nash_conv=max(0.0, nash_conv),
        exploitability=max(0.0, 0.5 * nash_conv),
        br0=br0,
        br1=br1,
    )


__all__ = [
    "AUTHORITY",
    "SCHEMA",
    "ExactTwoStreetBestResponse",
    "ExactTwoStreetNashConv",
    "exact_best_response",
    "profile_with_pure_response",
    "replay_best_response_value",
    "exact_nash_conv",
]
