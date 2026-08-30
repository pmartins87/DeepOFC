from __future__ import annotations

from external_06r0_conditioned_solver import FROZEN_FIXTURES, build_conditioned_fixture
from external_06r1_belief_correct import build_belief_support
from external_06r2_heldout_panel import build_unique_heldout_panel, panel_probe


def _fixture(name: str):
    spec = next(x for x in FROZEN_FIXTURES if x.name == name)
    root = build_conditioned_fixture(spec)
    support = build_belief_support(root, spec)
    return spec, root, support


def test_r3_panels_are_deterministic_unique_and_information_exact():
    for name, seed in (("R3_P0_A", 306201), ("R3_P1_A", 306211)):
        spec, root, support = _fixture(name)
        a = build_unique_heldout_panel(root, spec, support, seed=seed, size=8)
        b = build_unique_heldout_panel(root, spec, support, seed=seed, size=8)
        assert a.plan_sha256s == b.plan_sha256s
        assert a.panel_sha256 == b.panel_sha256
        probe = panel_probe(a, root)
        assert probe["size"] == 8
        assert probe["unique_plan_count"] == 8
        assert probe["all_root_information_exact"]


def test_frozen_panel_seeds_materialize_different_panels():
    spec, root, support = _fixture("R3_P0_A")
    a = build_unique_heldout_panel(root, spec, support, seed=306201, size=8)
    b = build_unique_heldout_panel(root, spec, support, seed=306202, size=8)
    assert a.panel_sha256 != b.panel_sha256
    assert a.plan_sha256s != b.plan_sha256s
