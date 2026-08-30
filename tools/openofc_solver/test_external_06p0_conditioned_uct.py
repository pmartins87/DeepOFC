from __future__ import annotations

from external_06p0_conditioned_uct import ConditionedSuitCanonicalISUCT
from external_06r0_conditioned_solver import FROZEN_FIXTURES, build_conditioned_fixture


def _r1_p0_root():
    spec = next(spec for spec in FROZEN_FIXTURES if spec.name == "R1_P0_A")
    return build_conditioned_fixture(spec)


def test_isuct_same_seed_is_exact() -> None:
    root = _r1_p0_root()
    a = ConditionedSuitCanonicalISUCT(base_root=root, seed=99101, exploration=2.0)
    b = ConditionedSuitCanonicalISUCT(base_root=root, seed=99101, exploration=2.0)
    a.run(32)
    b.run(32)
    assert a.visit_accounting_exact()
    assert b.visit_accounting_exact()
    assert a.root_readout() == b.root_readout()
    assert a.best_root_action_key() == b.best_root_action_key()


def test_isuct_root_visit_accounting_and_action_coverage() -> None:
    root = _r1_p0_root()
    solver = ConditionedSuitCanonicalISUCT(base_root=root, seed=99102, exploration=2.0)
    solver.run(256)
    rows = solver.root_readout()
    assert solver.visit_accounting_exact()
    assert len(rows) > 1
    assert sum(row.visits for row in rows) == 256
    # 256 trajectories are enough to force at least two distinct root actions
    # regardless of how many legal actions the R1 fixture has.
    assert sum(row.visits > 0 for row in rows) >= 2


def test_fixed_and_future_resampled_uct_keep_same_root_action_space() -> None:
    root = _r1_p0_root()
    fixed = ConditionedSuitCanonicalISUCT(
        base_root=root,
        seed=99103,
        exploration=2.0,
        resample_future=False,
    )
    sampled = ConditionedSuitCanonicalISUCT(
        base_root=root,
        seed=99103,
        exploration=2.0,
        resample_future=True,
    )
    fixed.run(8)
    sampled.run(8)
    assert {
        row.canonical_action_key for row in fixed.root_readout()
    } == {
        row.canonical_action_key for row in sampled.root_readout()
    }
