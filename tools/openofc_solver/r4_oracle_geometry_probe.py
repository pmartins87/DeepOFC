from __future__ import annotations

import json
from math import comb

from engine import full_deck
from external_06r0_conditioned_solver import FROZEN_FIXTURES, build_conditioned_fixture
from external_06r1_belief_correct import build_belief_support
from external_06s0_suit_automorphism import canonical_information_state
from strategic_cfr import child_state, legal_action_pairs


def main() -> None:
    spec = next(x for x in FROZEN_FIXTURES if x.name == "R4_P0_A")
    root = build_conditioned_fixture(spec)
    support = build_belief_support(root, spec)

    root_pairs = legal_action_pairs(root)
    root_action_count = len(root_pairs)

    used_base = set(root.plan.opening[0]) | set(root.plan.opening[1])
    # Hero's own packets through R4 are known at the root.
    for r in range(1, 5):
        used_base.update(root.plan.rounds[r - 1][0])
    # Opponent's public placed cards from R1-R3 are known; one discard each is hidden.
    for event in root.public_history:
        if event.player == 1 and 1 <= event.round_index <= 3:
            from engine import Card
            used_base.update(Card.parse(token) for token, _row in event.placements)

    hidden_count = support.hidden_history_count
    worlds_per_history = None
    total_worlds = 0
    if hidden_count:
        # After fixing a compatible 3-card hidden-discard history, the only
        # unresolved packet at R4 P0 is P1's three-card R4 packet.
        one_history = support.hidden_histories[0]
        used = set(used_base) | set(one_history)
        remaining = len([c for c in full_deck(2) if c not in used])
        worlds_per_history = comb(remaining, 3)
        total_worlds = hidden_count * worlds_per_history
    else:
        remaining = None

    p1_action_counts = []
    for _key, action in root_pairs:
        child = child_state(root, action)
        p1_action_counts.append(len(legal_action_pairs(child)))

    payload = {
        "fixture": spec.name,
        "hidden_history_count": hidden_count,
        "root_action_count": root_action_count,
        "remaining_cards_after_one_hidden_history": remaining,
        "worlds_per_hidden_history": worlds_per_history,
        "total_posterior_worlds_expected": total_worlds,
        "p1_action_count_min": min(p1_action_counts) if p1_action_counts else 0,
        "p1_action_count_max": max(p1_action_counts) if p1_action_counts else 0,
        "p1_action_count_mean": (sum(p1_action_counts) / len(p1_action_counts)) if p1_action_counts else 0.0,
        "root_canonical_key_prefix": canonical_information_state(root)[0][:80],
        "naive_terminal_evaluation_upper_bound": (
            total_worlds * sum(p1_action_counts)
        ),
    }
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
