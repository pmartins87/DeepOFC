from __future__ import annotations

from itertools import islice

from external_06r0_conditioned_solver import FROZEN_FIXTURES, build_conditioned_fixture
from external_06r1_belief_correct import build_belief_support, iter_exact_r4_p0_worlds
from r4_exact_worlds_direct import iter_exact_r4_p0_worlds_direct


def test_direct_worlds_match_replayed_worlds_prefix():
    spec = next(x for x in FROZEN_FIXTURES if x.name == "R4_P0_A")
    root = build_conditioned_fixture(spec)
    support = build_belief_support(root, spec)
    old = list(islice(iter_exact_r4_p0_worlds(root, spec, support), 128))
    new = list(islice(iter_exact_r4_p0_worlds_direct(root, spec, support, validate_each_world=True), 128))
    assert len(old) == len(new) == 128
    assert new == old
