from __future__ import annotations

"""Exact opponent-counterfactual-reach geometry for M5R bridge calibration.

This module is deliberately descriptive.  It traverses the same exact reduced
three-round tree used by the M5R exact-BR ladder and records every opponent
child reach at which the conservative interval bridge would be *allowed* to
cut.  It never actually prunes a branch and never evaluates terminal utility.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass
import math
from typing import Any, Mapping

from deepofc.actions import NormalPlacementAction
from deepofc.sequential import HUPlayerObservation, HUSequentialNormalState

AUTHORITY = "M5R_REDUCED_EXACT_REACH_GEOMETRY_ONLY"
SCHEMA = "openofc-m5r-three-round-reach-geometry-cell-v1"
EPS = 1e-15

StrategyProfile = Mapping[
    HUPlayerObservation,
    Mapping[NormalPlacementAction, float],
]


@dataclass(frozen=True)
class ReachLevel:
    float_hex: str
    value: float
    count: int


@dataclass(frozen=True)
class OpponentReachGeometry:
    player: int
    terminal_histories: int
    candidate_opponent_children: int
    zero_reach_candidates: int
    positive_reach_levels: tuple[ReachLevel, ...]
    positive_reach_levels_by_round: dict[int, tuple[ReachLevel, ...]]
    responding_player_probability_multiplications: int = 0
    pruning_executed: bool = False
    authority: str = AUTHORITY
    schema: str = SCHEMA
    production_certification_eligible: bool = False
    real_routes_certified: int = 0


def _level_rows(counter: Counter[str]) -> tuple[ReachLevel, ...]:
    rows: list[ReachLevel] = []
    for hex_value, count in counter.items():
        value = float.fromhex(hex_value)
        if not math.isfinite(value) or value <= 0.0:
            raise AssertionError("positive reach counter contains non-positive/non-finite value")
        rows.append(ReachLevel(float_hex=hex_value, value=value, count=int(count)))
    rows.sort(key=lambda row: (row.value, row.float_hex))
    return tuple(rows)


def opponent_reach_geometry(
    game: Any,
    profile: StrategyProfile,
    player: int,
) -> OpponentReachGeometry:
    """Traverse the full reduced tree and inventory legal opponent-cut reaches.

    Counterfactual reach is chance times opponent behavior only.  Responding
    actions are fully enumerated and do not alter reach.  A candidate cut site
    exists only on an opponent child after at least one responding-player action
    has occurred, exactly matching the authority firewall of the interval bridge.
    """

    if player not in (0, 1):
        raise ValueError("player must be 0 or 1")

    terminal_histories = 0
    candidates = 0
    zero_candidates = 0
    global_levels: Counter[str] = Counter()
    by_round: dict[int, Counter[str]] = defaultdict(Counter)

    def recurse(
        state: HUSequentialNormalState,
        opponent_reach: float,
        own_action_count: int,
    ) -> None:
        nonlocal terminal_histories, candidates, zero_candidates

        if not math.isfinite(opponent_reach) or opponent_reach < -EPS:
            raise ValueError("invalid opponent counterfactual reach")
        if state.terminal:
            terminal_histories += 1
            if own_action_count != 3:
                raise AssertionError(
                    f"responding player must act exactly three times, got {own_action_count}"
                )
            return

        info = game.info(state)
        legal = game.actions(info)
        actor = state.acting_chair

        if actor == player:
            expected_depth = info.state.round_index - 2
            if expected_depth not in (0, 1, 2):
                raise AssertionError(f"unexpected responding decision depth: {expected_depth}")
            if own_action_count != expected_depth:
                raise AssertionError(
                    "perfect-recall depth mismatch in reach geometry: "
                    f"round={info.state.round_index} prior_own={own_action_count}"
                )
            for action in legal:
                recurse(
                    game.transition(state, action),
                    opponent_reach,
                    own_action_count + 1,
                )
            return

        distribution = game.distribution(profile, info)
        for action in legal:
            probability = float(distribution[action])
            if not math.isfinite(probability) or probability < -EPS:
                raise ValueError("opponent distribution contains invalid probability")
            child_reach = opponent_reach * probability
            child = game.transition(state, action)
            if own_action_count > 0:
                candidates += 1
                if child_reach <= 0.0:
                    zero_candidates += 1
                else:
                    hex_value = child_reach.hex()
                    global_levels[hex_value] += 1
                    by_round[int(state.round_index)][hex_value] += 1
            recurse(child, child_reach, own_action_count)

    cp = float(game.chance_probability)
    if not math.isfinite(cp) or cp <= 0.0:
        raise ValueError("chance probability must be finite and positive")
    for outcome in game.outcomes:
        recurse(game.initial_state(outcome), cp, 0)

    positive = _level_rows(global_levels)
    if candidates <= 0:
        raise AssertionError("reach geometry found no legal cut-candidate opponent children")
    if not positive:
        raise AssertionError("reach geometry found no positive reach levels")

    return OpponentReachGeometry(
        player=player,
        terminal_histories=terminal_histories,
        candidate_opponent_children=candidates,
        zero_reach_candidates=zero_candidates,
        positive_reach_levels=positive,
        positive_reach_levels_by_round={
            round_index: _level_rows(counter)
            for round_index, counter in sorted(by_round.items())
        },
    )