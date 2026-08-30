from __future__ import annotations

import random

from engine import score_heads_up
from external_06r0_conditioned_solver import FROZEN_FIXTURES, build_conditioned_fixture
from external_06r1_belief_correct import build_belief_support, sample_belief_root
from r4_exact_oracle_cached import exact_points_from_boards
from strategic_cfr import child_state, legal_action_pairs


def test_cached_terminal_points_match_engine():
    spec = next(x for x in FROZEN_FIXTURES if x.name == "R4_P0_A")
    root = build_conditioned_fixture(spec)
    support = build_belief_support(root, spec)
    rng = random.Random(604001)
    for _ in range(16):
        world = sample_belief_root(root, spec, support, rng)
        for _key0, a0 in legal_action_pairs(world)[:3]:
            p1 = child_state(world, a0)
            for _key1, a1 in legal_action_pairs(p1):
                terminal = child_state(p1, a1)
                expected = float(score_heads_up(terminal.boards[0], terminal.boards[1]).points)
                actual = exact_points_from_boards(terminal.boards[0], terminal.boards[1])
                assert actual == expected
