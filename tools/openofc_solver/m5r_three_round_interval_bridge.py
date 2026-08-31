from __future__ import annotations

"""Conservative three-round BR intervals for the M5R exact validation ladder.

The implementation mirrors the exact perfect-recall BR dynamic program, but it
may replace sufficiently low counterfactual-reach *opponent* child subtrees with
a rigorous state-local utility interval.  Responding-player actions are never
pruned and their behavioral probabilities are never part of reach.
"""

from dataclasses import dataclass
import math
from typing import Any, Callable, Mapping

from deepofc.actions import NormalPlacementAction
from deepofc.sequential import HUPlayerObservation, HUSequentialNormalState
from deepofc.state import PlayerBoard
from m5r_full_game_remainder_envelope import p0_raw_point_interval

AUTHORITY = "M5R_THREE_ROUND_CONSERVATIVE_BR_INTERVAL_VALIDATION_ONLY"
SCHEMA = "openofc-m5r-three-round-br-interval-v1"
EPS = 1e-15

StateIntervalFn = Callable[[PlayerBoard, PlayerBoard], tuple[float, float]]
StrategyProfile = Mapping[
    HUPlayerObservation,
    Mapping[NormalPlacementAction, float],
]


@dataclass
class _Interval:
    lower: float = 0.0
    upper: float = 0.0

    def add(self, lower: float, upper: float) -> None:
        lo = float(lower)
        hi = float(upper)
        if not math.isfinite(lo) or not math.isfinite(hi):
            raise ValueError("interval contribution must be finite")
        if lo > hi + 1e-12:
            raise ValueError("interval contribution is inverted")
        self.lower += lo
        self.upper += hi


@dataclass(frozen=True)
class ThreeRoundBRInterval:
    player: int
    prune_reach_threshold: float
    lower_br_value: float
    upper_br_value: float
    interval_width: float
    terminal_utility_evaluations: int
    pruned_opponent_branches: int
    zero_reach_pruned_branches: int
    state_local_envelope_calls: int
    state_local_envelope_reach_mass: float
    state_local_envelope_weighted_width: float
    min_state_local_p0_width: float | None
    max_state_local_p0_width: float | None
    represented_responding_infosets: int
    represented_responding_actions: int
    own_action_pruning_count: int
    authority: str = AUTHORITY
    schema: str = SCHEMA
    production_certification_eligible: bool = False
    real_routes_certified: int = 0


def conservative_three_round_br_interval(
    game: Any,
    profile: StrategyProfile,
    player: int,
    *,
    prune_reach_threshold: float,
    p0_state_interval: StateIntervalFn = p0_raw_point_interval,
) -> ThreeRoundBRInterval:
    """Return a rigorous interval containing the responding player's BR value.

    Counterfactual reach consists only of chance and opponent probabilities.
    A cut is allowed only on an opponent child and only after at least one
    responding-player action is present in perfect recall.  The omitted future
    decision process can then contribute no less/no more than the state-local
    terminal utility envelope, so that contribution is attached directly to the
    current own predecessor action.  Later max propagation remains conservative
    even when the omitted future information set is also reached elsewhere.
    """

    if player not in (0, 1):
        raise ValueError("player must be 0 or 1")
    threshold = float(prune_reach_threshold)
    if not math.isfinite(threshold) or threshold < 0.0:
        raise ValueError("prune_reach_threshold must be finite and non-negative")

    values_by_depth: dict[
        int,
        dict[HUPlayerObservation, dict[NormalPlacementAction, _Interval]],
    ] = {0: {}, 1: {}, 2: {}}
    parent: dict[
        HUPlayerObservation,
        tuple[HUPlayerObservation, NormalPlacementAction],
    ] = {}

    terminal_evals = 0
    pruned_opponent = 0
    zero_reach_pruned = 0
    envelope_calls = 0
    envelope_reach_mass = 0.0
    envelope_weighted_width = 0.0
    min_local_width: float | None = None
    max_local_width: float | None = None

    def bucket_for(
        depth: int,
        info: HUPlayerObservation,
    ) -> dict[NormalPlacementAction, _Interval]:
        if depth not in (0, 1, 2):
            raise AssertionError(f"unexpected three-round BR depth {depth}")
        return values_by_depth[depth].setdefault(
            info,
            {action: _Interval() for action in game.actions(info)},
        )

    def add_skipped_child(
        child: HUSequentialNormalState,
        reach: float,
        own_sequence: tuple[
            tuple[HUPlayerObservation, NormalPlacementAction], ...
        ],
    ) -> None:
        nonlocal pruned_opponent, zero_reach_pruned
        nonlocal envelope_calls, envelope_reach_mass, envelope_weighted_width
        nonlocal min_local_width, max_local_width

        if not own_sequence:
            raise AssertionError("cannot attach skipped value before first own action")
        info, action = own_sequence[-1]
        depth = len(own_sequence) - 1
        if depth not in (0, 1, 2):
            raise AssertionError("invalid own predecessor depth at prune")

        p0_lo_raw, p0_hi_raw = p0_state_interval(child.boards[0], child.boards[1])
        p0_lo = float(p0_lo_raw)
        p0_hi = float(p0_hi_raw)
        if not math.isfinite(p0_lo) or not math.isfinite(p0_hi):
            raise ValueError("state-local envelope must be finite")
        if p0_lo > p0_hi + 1e-12:
            raise ValueError("state-local P0 envelope is inverted")
        own_lo, own_hi = (
            (p0_lo, p0_hi) if player == 0 else (-p0_hi, -p0_lo)
        )
        bucket_for(depth, info)[action].add(reach * own_lo, reach * own_hi)

        width = p0_hi - p0_lo
        pruned_opponent += 1
        if reach <= EPS:
            zero_reach_pruned += 1
        envelope_calls += 1
        envelope_reach_mass += reach
        envelope_weighted_width += reach * width
        min_local_width = width if min_local_width is None else min(min_local_width, width)
        max_local_width = width if max_local_width is None else max(max_local_width, width)

    def recurse(
        state: HUSequentialNormalState,
        opponent_reach: float,
        own_sequence: tuple[
            tuple[HUPlayerObservation, NormalPlacementAction], ...
        ],
    ) -> None:
        nonlocal terminal_evals

        if state.terminal:
            terminal_evals += 1
            if len(own_sequence) != 3:
                raise AssertionError(
                    f"responding player must act three times, got {len(own_sequence)}"
                )
            info, action = own_sequence[-1]
            u0 = float(game.terminal_u0(state))
            own_u = u0 if player == 0 else -u0
            exact = opponent_reach * own_u
            bucket_for(2, info)[action].add(exact, exact)
            return

        info = game.info(state)
        actor = state.acting_chair
        legal = game.actions(info)

        if actor == player:
            depth = info.state.round_index - 2
            if depth not in (0, 1, 2):
                raise AssertionError(f"unexpected responding decision depth {depth}")
            if len(own_sequence) != depth:
                raise AssertionError(
                    "perfect-recall decision-depth mismatch: "
                    f"round={info.state.round_index} prior_own={len(own_sequence)}"
                )
            bucket_for(depth, info)
            if depth > 0:
                predecessor = own_sequence[-1]
                previous = parent.setdefault(info, predecessor)
                if previous != predecessor:
                    raise AssertionError(
                        "perfect-recall violation: responding infoset has multiple own predecessors"
                    )
            # Authority firewall: no threshold check exists on this path.
            for action in legal:
                recurse(
                    game.transition(state, action),
                    opponent_reach,
                    (*own_sequence, (info, action)),
                )
            return

        distribution = game.distribution(profile, info)
        for action in legal:
            probability = float(distribution[action])
            if probability < -EPS or not math.isfinite(probability):
                raise ValueError("opponent distribution contains invalid probability")
            child_reach = opponent_reach * probability
            child = game.transition(state, action)
            if own_sequence and child_reach <= threshold + EPS:
                add_skipped_child(child, child_reach, own_sequence)
                continue
            recurse(child, child_reach, own_sequence)

    for outcome in game.outcomes:
        recurse(game.initial_state(outcome), float(game.chance_probability), ())

    for depth in (2, 1, 0):
        for info, action_intervals in values_by_depth[depth].items():
            if not action_intervals:
                raise AssertionError("responding infoset has no legal actions")
            lower_best = max(interval.lower for interval in action_intervals.values())
            upper_best = max(interval.upper for interval in action_intervals.values())
            if lower_best > upper_best + 1e-12:
                raise AssertionError("best-response interval inverted at infoset")
            if depth == 0:
                continue
            parent_info, parent_action = parent[info]
            bucket_for(depth - 1, parent_info)[parent_action].add(lower_best, upper_best)

    lower_total = 0.0
    upper_total = 0.0
    for action_intervals in values_by_depth[0].values():
        lower_total += max(interval.lower for interval in action_intervals.values())
        upper_total += max(interval.upper for interval in action_intervals.values())

    if lower_total > upper_total + 1e-12:
        raise AssertionError("aggregate three-round BR interval inverted")

    represented_infosets = sum(len(layer) for layer in values_by_depth.values())
    represented_actions = sum(
        len(actions)
        for layer in values_by_depth.values()
        for actions in layer.values()
    )
    return ThreeRoundBRInterval(
        player=player,
        prune_reach_threshold=threshold,
        lower_br_value=lower_total,
        upper_br_value=upper_total,
        interval_width=upper_total - lower_total,
        terminal_utility_evaluations=terminal_evals,
        pruned_opponent_branches=pruned_opponent,
        zero_reach_pruned_branches=zero_reach_pruned,
        state_local_envelope_calls=envelope_calls,
        state_local_envelope_reach_mass=envelope_reach_mass,
        state_local_envelope_weighted_width=envelope_weighted_width,
        min_state_local_p0_width=min_local_width,
        max_state_local_p0_width=max_local_width,
        represented_responding_infosets=represented_infosets,
        represented_responding_actions=represented_actions,
        own_action_pruning_count=0,
    )
