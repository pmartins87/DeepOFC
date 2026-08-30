from __future__ import annotations

"""Exact combinatorial R4 P0 oracle with no intermediate HUState materialization.

At R4 P0, once Hero chooses a root action, Hero's final board is fixed. For one
compatible opponent hidden-discard history, the only unresolved chance event is
P1's current three-card packet. P1 observes that packet and its own historical
discards, so every (history, packet) pair is a distinct P1 information state.
P1 may therefore take its exact best legal R4 response independently in each
such world. This module averages those exact minima over the same uniform
posterior worlds used by EXT-06R1.
"""

from itertools import combinations
import math

from engine import apply_action, full_deck, legal_actions
from external_06r0_conditioned_solver import ConditionedFixtureSpec
from external_06r1_belief_correct import (
    BeliefSupport,
    R4ExactOracle,
    _assignments_for_history,
    _canonical_pairs,
)
from r4_exact_oracle_cached import exact_points_from_boards
from strategic_cfr import HUState


def exact_r4_p0_oracle_combinatorial(
    root: HUState,
    spec: ConditionedFixtureSpec,
    support: BeliefSupport,
) -> R4ExactOracle:
    if (root.round_index, root.actor) != (4, 0):
        raise ValueError("combinatorial exact oracle requires R4 P0")
    if (spec.round_index, spec.actor) != (4, 0):
        raise ValueError("fixture spec must be R4 P0")
    root_key, root_pairs = _canonical_pairs(root)
    if root_key != support.root_canonical_information_state_key:
        raise AssertionError("oracle root canonical key differs from belief support")
    if support.opponent != 1:
        raise AssertionError("R4 P0 opponent must be P1")

    hero_incoming = root.plan.incoming(4, 0)
    hero_final_by_key = {
        canonical_key: apply_action(root.boards[0], hero_incoming, action)
        for canonical_key, action in root_pairs
    }

    totals = {key: 0.0 for key, _action in root_pairs}
    world_count = 0
    p1_action_count: int | None = None

    for history in support.hidden_histories:
        opening, assignments = _assignments_for_history(root, support, history)
        used = set(opening[0] + opening[1])
        for packet in assignments.values():
            used.update(packet)
        remaining = [card for card in full_deck(2) if card not in used]

        for packet_raw in combinations(remaining, 3):
            packet = tuple(sorted(packet_raw))
            responses = legal_actions(root.boards[1], packet, 4)
            if not responses:
                raise AssertionError("R4 P1 packet has no legal response")
            if p1_action_count is None:
                p1_action_count = len(responses)
            elif len(responses) != p1_action_count:
                raise AssertionError("R4 P1 legal-action count varies across worlds")

            opponent_finals = tuple(
                apply_action(root.boards[1], packet, response)
                for response in responses
            )
            for root_action_key, hero_final in hero_final_by_key.items():
                best_response_value = min(
                    exact_points_from_boards(hero_final, opponent_final)
                    for opponent_final in opponent_finals
                )
                if not math.isfinite(best_response_value):
                    raise AssertionError("combinatorial terminal value is non-finite")
                totals[root_action_key] += best_response_value
            world_count += 1

    if world_count <= 0:
        raise AssertionError("exact R4 posterior has no worlds")

    values = sorted(
        (key, total / world_count)
        for key, total in totals.items()
    )
    best_value = max(value for _key, value in values)
    best_keys = sorted(key for key, value in values if abs(value - best_value) <= 1e-12)
    p1_counts = tuple((key, world_count) for key, _value in values)
    return R4ExactOracle(
        root_action_values=tuple(values),
        best_action_key=best_keys[0],
        best_value=best_value,
        posterior_worlds=world_count,
        p1_information_states_by_root_action=p1_counts,
    )
