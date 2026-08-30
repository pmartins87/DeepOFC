from __future__ import annotations

import random

from external_06r0_conditioned_solver import FROZEN_FIXTURES, build_conditioned_fixture
from external_06r1_belief_correct import BeliefCorrectISUCT, BeliefCorrectMCCFR, build_belief_support, sample_belief_root
from external_06s0_suit_automorphism import canonical_information_state, canonical_legal_action_keys
from strategic_cfr import information_state_key


def fixture():
    spec = next(x for x in FROZEN_FIXTURES if x.name == "R4_P0_A")
    return spec, build_conditioned_fixture(spec)


def test_support_deterministic_nonempty():
    spec, root = fixture()
    a = build_belief_support(root, spec)
    b = build_belief_support(root, spec)
    assert a.hidden_history_count > 0
    assert a.hidden_histories == b.hidden_histories
    assert a.opponent_hidden_event_rounds == (1, 2, 3)


def test_samples_keep_root_information():
    spec, root = fixture()
    support = build_belief_support(root, spec)
    rng = random.Random(606101)
    raw = information_state_key(root)
    canonical = canonical_information_state(root)[0]
    actions = canonical_legal_action_keys(root)
    seen = set()
    for _ in range(16):
        sampled = sample_belief_root(root, spec, support, rng)
        assert information_state_key(sampled) == raw
        assert canonical_information_state(sampled)[0] == canonical
        assert canonical_legal_action_keys(sampled) == actions
        seen.add(tuple(map(str, sampled.plan.dealt_cards())))
    assert len(seen) > 1


def test_search_arms_smoke():
    spec, root = fixture()
    support = build_belief_support(root, spec)
    uct = BeliefCorrectISUCT(base_root=root, spec=spec, support=support, seed=606102)
    uct.run(8)
    assert uct.visit_accounting_exact()
    mccfr = BeliefCorrectMCCFR(base_root=root, spec=spec, support=support, seed=606103)
    mccfr.run(4)
    assert mccfr.iterations == 4
    assert mccfr.episodes == 8
    key = canonical_information_state(root)[0]
    assert key in mccfr.nodes
    assert abs(sum(mccfr.nodes[key].average_policy()) - 1.0) <= 1e-12
