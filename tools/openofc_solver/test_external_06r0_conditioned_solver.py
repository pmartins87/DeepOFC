from __future__ import annotations

from external_06r0_conditioned_solver import (
    FROZEN_FIXTURES,
    ConditionedSuitCanonicalOutcomeSamplingMCCFR,
    build_conditioned_fixture,
    checkpoint_semantic_bytes,
    remaining_decisions_per_iteration,
    root_probe,
)
from external_06s0_suit_automorphism import canonical_information_state


def test_frozen_conditioned_fixtures_reach_exact_target() -> None:
    for spec in FROZEN_FIXTURES:
        root = build_conditioned_fixture(spec)
        assert (root.round_index, root.actor) == (spec.round_index, spec.actor)
        assert not root.terminal()
        assert remaining_decisions_per_iteration(root) >= 2


def test_future_resampling_preserves_root_information_and_changes_future() -> None:
    for index, spec in enumerate(FROZEN_FIXTURES):
        root = build_conditioned_fixture(spec)
        probe = root_probe(root, sample_seed=77100 + index, samples=8)
        assert probe["raw_and_canonical_root_information_exact"]
        assert probe["unique_sampled_plan_sha256"] > 1
        assert probe["root_legal_action_count"] > 0


def test_conditioned_solver_is_same_seed_exact_and_visit_accounting_is_exact() -> None:
    spec = next(spec for spec in FROZEN_FIXTURES if spec.name == "R3_P0_A")
    root = build_conditioned_fixture(spec)
    a = ConditionedSuitCanonicalOutcomeSamplingMCCFR(
        base_root=root,
        resample_future=True,
        seed=88001,
        epsilon=0.6,
        cfr_plus=True,
    )
    b = ConditionedSuitCanonicalOutcomeSamplingMCCFR(
        base_root=root,
        resample_future=True,
        seed=88001,
        epsilon=0.6,
        cfr_plus=True,
    )
    a.run(6)
    b.run(6)
    assert checkpoint_semantic_bytes(a) == checkpoint_semantic_bytes(b)

    total_visits = sum(node.visits for node in a.nodes.values())
    assert total_visits == 6 * remaining_decisions_per_iteration(root)
    root_key, _ = canonical_information_state(root)
    assert a.nodes[root_key].visits == 6


def test_fixed_and_resampled_arms_share_exact_canonical_root() -> None:
    spec = next(spec for spec in FROZEN_FIXTURES if spec.name == "R2_P1_A")
    root = build_conditioned_fixture(spec)
    root_key, _ = canonical_information_state(root)

    fixed = ConditionedSuitCanonicalOutcomeSamplingMCCFR(
        base_root=root,
        resample_future=False,
        seed=88002,
        epsilon=0.6,
        cfr_plus=True,
    )
    sampled = ConditionedSuitCanonicalOutcomeSamplingMCCFR(
        base_root=root,
        resample_future=True,
        seed=88002,
        epsilon=0.6,
        cfr_plus=True,
    )
    fixed.run(2)
    sampled.run(2)
    assert root_key in fixed.nodes
    assert root_key in sampled.nodes
    assert fixed.nodes[root_key].action_keys == sampled.nodes[root_key].action_keys
