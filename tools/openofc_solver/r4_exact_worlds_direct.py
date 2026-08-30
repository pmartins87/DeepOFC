from __future__ import annotations

"""Direct exact R4 P0 posterior materialization after validated hidden support.

`build_belief_support` already proves each hidden-discard history reproduces the
frozen public prefix. At R4 P0, varying only P1's not-yet-dealt current packet
cannot change that prefix. Therefore we can construct the root HUState directly
instead of replaying all eight earlier actions for every future packet.
"""

from itertools import combinations
from typing import Iterator

from engine import full_deck
from external_06r0_conditioned_solver import ConditionedFixtureSpec
from external_06r1_belief_correct import (
    BeliefSupport,
    _assignments_for_history,
    _build_plan,
)
from strategic_cfr import HUState, information_state_key


def iter_exact_r4_p0_worlds_direct(
    root: HUState,
    spec: ConditionedFixtureSpec,
    support: BeliefSupport,
    *,
    validate_each_world: bool = False,
) -> Iterator[HUState]:
    if (root.round_index, root.actor) != (4, 0):
        raise ValueError("direct exact world enumeration requires R4 P0")
    if (spec.round_index, spec.actor) != (4, 0):
        raise ValueError("fixture spec must be R4 P0")
    if support.opponent != 1:
        raise AssertionError("R4 P0 opponent must be P1")

    root_key = information_state_key(root)
    for history in support.hidden_histories:
        opening, assignments = _assignments_for_history(root, support, history)
        used = set(opening[0] + opening[1])
        for packet in assignments.values():
            used.update(packet)
        remaining = [card for card in full_deck(2) if card not in used]
        for packet in combinations(remaining, 3):
            world_assignments = dict(assignments)
            world_assignments[(4, 1)] = tuple(sorted(packet))
            plan = _build_plan(opening=opening, assignments=world_assignments)
            sampled = HUState(
                plan=plan,
                round_index=4,
                actor=0,
                boards=root.boards,
                discards=(tuple(root.discards[0]), tuple(history)),
                public_history=root.public_history,
            )
            if validate_each_world and information_state_key(sampled) != root_key:
                raise AssertionError("direct exact R4 world changed root information")
            yield sampled
