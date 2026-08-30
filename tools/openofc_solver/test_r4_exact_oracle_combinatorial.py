from __future__ import annotations

from itertools import islice

from engine import apply_action, legal_actions
from external_06r0_conditioned_solver import FROZEN_FIXTURES, build_conditioned_fixture
from external_06r1_belief_correct import (
    _canonical_pairs,
    build_belief_support,
    iter_exact_r4_p0_worlds,
)
from r4_exact_oracle_cached import exact_points_from_boards
from strategic_cfr import child_state, legal_action_pairs, terminal_utility


def test_combinatorial_leaf_minima_match_full_state_tree():
    spec = next(x for x in FROZEN_FIXTURES if x.name == "R4_P0_A")
    root = build_conditioned_fixture(spec)
    support = build_belief_support(root, spec)
    root_pairs = _canonical_pairs(root)[1]
    hero_incoming = root.plan.incoming(4, 0)

    for world in islice(iter_exact_r4_p0_worlds(root, spec, support), 64):
        packet = tuple(world.plan.incoming(4, 1))
        direct_responses = legal_actions(root.boards[1], packet, 4)
        assert direct_responses
        for canonical_key, root_action in root_pairs:
            hero_final = apply_action(root.boards[0], hero_incoming, root_action)
            direct_min = min(
                exact_points_from_boards(
                    hero_final,
                    apply_action(root.boards[1], packet, response),
                )
                for response in direct_responses
            )

            world_map = dict(_canonical_pairs(world)[1])
            child = child_state(world, world_map[canonical_key])
            tree_min = min(
                terminal_utility(child_state(child, response), 0)
                for _key, response in legal_action_pairs(child)
            )
            assert direct_min == tree_min
