from __future__ import annotations

"""Semantics-preserving memoized exact R4 P0 oracle.

This is an engineering accelerator, not a new strategic method. It computes
exactly the same Hero-root value against P1 best response as the belief-correct
06R1 oracle, but memoizes resolved final boards and directly materializes
already-certified R4 posterior worlds so Joker substitution and prefix replay
are not repeated.

Critical semantic rule: P1 chooses ONE response per P1 information state. Two
posterior worlds may map to the same P1 infoset because P1 does not observe all
of P0's hidden information. Those worlds must be grouped before best response;
minimizing independently per world would give P1 illicit hidden-world knowledge.
"""

from functools import lru_cache
import math

from engine import Board, apply_action, resolve_board
from external_06r1_belief_correct import BeliefSupport, R4ExactOracle, _canonical_pairs
from external_06r0_conditioned_solver import ConditionedFixtureSpec
from r4_exact_worlds_direct import iter_exact_r4_p0_worlds_direct
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
    root_key, root_pairs = _canonical_pairs(root)
    if root_key != support.root_canonical_information_state_key:
        raise AssertionError("oracle root canonical key differs from belief support")

    worlds = tuple(iter_exact_r4_p0_worlds_direct(root, spec, support))
    if not worlds:
        raise AssertionError("exact R4 posterior has no worlds")
    world_count = len(worlds)

    values: list[tuple[str, float]] = []
    p1_counts: list[tuple[str, int]] = []
    for canonical_root_action, _root_action in root_pairs:
        # Match external_06r1_belief_correct.exact_r4_p0_oracle exactly:
        # group posterior worlds by P1's raw information state, accumulate the
        # utility of each legal P1 action across all worlds in that infoset, and
        # only then let P1 choose the minimizing action for that infoset.
        grouped: dict[str, dict[str, float]] = {}
        action_sets: dict[str, tuple[str, ...]] = {}

        for world in worlds:
            _world_key, world_pairs = _canonical_pairs(world)
            world_map = dict(world_pairs)
            if canonical_root_action not in world_map:
                raise AssertionError("posterior world changed root canonical action set")
            child = child_state(world, world_map[canonical_root_action])
            if child.terminal() or child.actor != 1 or child.round_index != 4:
                raise AssertionError("R4 P0 action must lead to R4 P1")

            p1_key = information_state_key(child)
            pairs = tuple(legal_action_pairs(child))
            keys = tuple(key for key, _action in pairs)
            previous = action_sets.get(p1_key)
            if previous is None:
                action_sets[p1_key] = keys
                grouped[p1_key] = {key: 0.0 for key in keys}
            elif previous != keys:
                raise AssertionError("same P1 infoset produced different actions")

            incoming = child.plan.incoming(4, 1)
            for p1_action_key, p1_action in pairs:
                opponent_final = apply_action(child.boards[1], incoming, p1_action)
                value = exact_points_from_boards(child.boards[0], opponent_final)
                if not math.isfinite(value):
                    raise AssertionError("cached exact terminal value is non-finite")
                grouped[p1_key][p1_action_key] += value

        # All enumerated posterior worlds have equal chance weight under the
        # frozen payoff-blind prefix posterior. min(sum) within each infoset is
        # equivalent to choosing the minimum conditional expectation there;
        # division by world_count then applies the infoset reach probability.
        value = sum(min(action_sums.values()) for action_sums in grouped.values()) / world_count
        if not math.isfinite(value):
            raise AssertionError("cached exact root value is non-finite")
        values.append((canonical_root_action, value))
        p1_counts.append((canonical_root_action, len(grouped)))

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
