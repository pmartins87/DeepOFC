from __future__ import annotations

import math

from external_05h_mccfr_simple_average import OverlapExternalSamplingMCCFRSimpleAverage
from external_hidden_discard_overlap_strategic import OverlapExternalSamplingMCCFR
from test_external_05g_uniform_backward_completion import four_world_fixture


def test_simple_average_accumulator_does_not_change_current_mccfr_trajectory() -> None:
    base, worlds = four_world_fixture()
    seed = 20260829
    iterations = 64

    baseline = OverlapExternalSamplingMCCFR(base, worlds, seed=seed)
    averaged = OverlapExternalSamplingMCCFRSimpleAverage(base, worlds, seed=seed)
    baseline.run(iterations)
    averaged.run(iterations)

    assert averaged.current_profile() == baseline.current_profile()
    assert averaged.regrets == baseline.regrets
    assert averaged.action_sets == baseline.action_sets
    assert averaged.snapshot() == baseline.snapshot()


def test_simple_average_profile_is_deterministic_legal_and_normalized() -> None:
    base, worlds = four_world_fixture()
    first = OverlapExternalSamplingMCCFRSimpleAverage(base, worlds, seed=20260830)
    second = OverlapExternalSamplingMCCFRSimpleAverage(base, worlds, seed=20260830)
    first.run(64)
    second.run(64)

    p1 = first.average_profile()
    p2 = second.average_profile()
    assert p1 == p2
    assert p1
    assert first.average_snapshot() == second.average_snapshot()
    assert first.average_snapshot().average_information_states == len(p1)
    assert first.average_snapshot().average_policy_updates > 0

    for info_key, dist in p1.items():
        assert tuple(dist) == first.action_sets[info_key]
        assert all(math.isfinite(prob) and prob >= 0.0 for prob in dist.values())
        assert math.isclose(sum(dist.values()), 1.0, rel_tol=0.0, abs_tol=1e-12)
