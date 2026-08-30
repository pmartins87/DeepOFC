from __future__ import annotations

import random

from external_06r0_conditioned_solver import FROZEN_FIXTURES, build_conditioned_fixture
from external_06r2a_uniform_information_sampler import (
    information_safe_probe,
    plan_digest,
    sample_uniform_information_safe_world,
)
from external_06s0_suit_automorphism import canonical_information_state, canonical_legal_action_keys
from strategic_cfr import child_state, information_state_key, legal_action_pairs


def _roots():
    roots = [build_conditioned_fixture(spec) for spec in FROZEN_FIXTURES]
    r4p0 = next(root for root in roots if (root.round_index, root.actor) == (4, 0))
    first_action = legal_action_pairs(r4p0)[0][1]
    roots.append(child_state(r4p0, first_action))  # R4 P1 boundary
    return roots


def test_sampler_preserves_actor_information_across_boundaries():
    for index, root in enumerate(_roots()):
        raw = information_state_key(root)
        canonical = canonical_information_state(root)[0]
        actions = canonical_legal_action_keys(root)
        rng = random.Random(620000 + index)
        seen = set()
        for _ in range(16):
            sampled = sample_uniform_information_safe_world(root, rng)
            assert information_state_key(sampled) == raw
            assert canonical_information_state(sampled)[0] == canonical
            assert canonical_legal_action_keys(sampled) == actions
            assert len(sampled.plan.dealt_cards()) == 34
            assert len(set(sampled.plan.dealt_cards())) == 34
            seen.add(plan_digest(sampled))
        assert len(seen) > 1


def test_sampler_does_not_depend_on_concrete_opponent_hidden_realization():
    for index, root in enumerate(_roots()):
        alternate = sample_uniform_information_safe_world(root, random.Random(621000 + index))
        assert information_state_key(alternate) == information_state_key(root)
        a = sample_uniform_information_safe_world(root, random.Random(622000 + index))
        b = sample_uniform_information_safe_world(alternate, random.Random(622000 + index))
        assert plan_digest(a) == plan_digest(b)
        assert a.discards[root.actor] == b.discards[root.actor] == root.discards[root.actor]


def test_probe_is_reproducible():
    root = next(r for r in _roots() if (r.round_index, r.actor) == (3, 0))
    a = information_safe_probe(root, seed=623001, samples=16)
    b = information_safe_probe(root, seed=623001, samples=16)
    assert a == b
    assert a["unique_plans"] > 1
