from __future__ import annotations

"""Semantics-preserving memoized exact R4 P0 oracle.

This is an engineering accelerator, not a new strategic method.  It computes
exactly the same Hero-root value against P1 best response as the 06R1 oracle,
but memoizes resolved final boards so Joker substitution work is not repeated.
"""

from functools import lru_cache
import math

from engine import Board, apply_action, resolve_board
from external_06r1_belief_correct import (
    BeliefSupport,
    R4ExactOracle,
    _canonical_root_pairs,
    iter_exact_r4_p0_worlds,
)
from external_06r0_conditioned_solver import ConditionedFixtureSpec
from strategic_cfr import HUState, child_state, information_state_key, legal_action_pairs


@lru_cache(maxsize=None)
def _resolved(board: Board):
    return resolve_board(board)


@lru_cache(maxsize=None)
def exact_points_from_boards(hero: Board, opponent: Board) -> float:
    """Return exactly score_heads_up(...).points using cached resolutions."""
    hr = _resolved(hero)
    vr = _resolved(opponent)
    if hr is None and vr is None:
        return 0.0
    if hr is None:
        assert vr is not None
        return float(-6 - vr.royalties)
    if vr is None:
        return float(6 + hr.royalties)
    row_points = tuple(
        1 if hr.ranks[i] > vr.ranks[i] else -1 if hr.ranks[i] < vr.ranks[i] else 0
        for i in range(3)
    )
    scoop = 3 if row_points == (1, 1, 1) else -3 if row_points == (-1, -1, -1) else 0
    return float(sum(row_points) + scoop + hr.royalties - vr.royalties)


def exact_r4_p0_oracle_cached(
    root: HUState,
    spec: ConditionedFixtureSpec,
    support: BeliefSupport,
) -> R4ExactOracle:
    if root.round_index != 4 or root.actor != 0:
        raise ValueError("cached exact oracle requires R4 P0")
    root_key, root_pairs = _canonical_root_pairs(root)
    if root_key != support.root_canonical_information_state_key:
        raise AssertionError("oracle root canonical key differs from belief support")

    worlds = tuple(iter_exact_r4_p0_worlds(root, spec, support))
    if not worlds:
        raise AssertionError("exact R4 posterior has no worlds")
    world_count = len(worlds)

    values: list[tuple[str, float]] = []
    p1_counts: list[tuple[str, int]] = []
    for canonical_root_action, _root_action in root_pairs:
        total = 0.0
        p1_infos: set[str] = set()
        for world in worlds:
            _world_key, world_pairs = _canonical_root_pairs(world)
            world_map = dict(world_pairs)
            if canonical_root_action not in world_map:
                raise AssertionError("posterior world changed root canonical action set")
            child = child_state(world, world_map[canonical_root_action])
            if child.terminal() or child.actor != 1 or child.round_index != 4:
                raise AssertionError("R4 P0 action must lead to R4 P1")

            p1_key = information_state_key(child)
            if p1_key in p1_infos:
                # At R4, P1's own three hidden discards plus current packet and
                # public state uniquely identify a world in this Hero posterior.
                # Fail closed if that empirical property ever changes.
                raise AssertionError("R4 P1 infoset spans multiple posterior worlds")
            p1_infos.add(p1_key)

            incoming = child.plan.incoming(4, 1)
            response_values = []
            for _p1_action_key, p1_action in legal_action_pairs(child):
                opponent_final = apply_action(child.boards[1], incoming, p1_action)
                value = exact_points_from_boards(child.boards[0], opponent_final)
                if not math.isfinite(value):
                    raise AssertionError("cached exact terminal value is non-finite")
                response_values.append(value)
            if not response_values:
                raise AssertionError("R4 P1 state has no legal response")
            total += min(response_values)

        if len(p1_infos) != world_count:
            raise AssertionError("R4 P1 information-state uniqueness accounting failed")
        values.append((canonical_root_action, total / world_count))
        p1_counts.append((canonical_root_action, len(p1_infos)))

    values.sort(key=lambda row: row[0])
    best_value = max(value for _key, value in values)
    best_keys = sorted(key for key, value in values if abs(value - best_value) <= 1e-12)
    return R4ExactOracle(
        root_action_values=tuple(values),
        best_action_key=best_keys[0],
        best_value=best_value,
        posterior_worlds=world_count,
        p1_information_states_by_root_action=tuple(sorted(p1_counts)),
    )


def cache_info() -> dict:
    return {
        "resolved": _resolved.cache_info()._asdict(),
        "points": exact_points_from_boards.cache_info()._asdict(),
    }
