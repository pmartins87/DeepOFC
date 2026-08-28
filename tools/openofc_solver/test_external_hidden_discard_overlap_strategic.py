from __future__ import annotations

import math

from external_hidden_discard_overlap_strategic import (
    AUTHORITY,
    OverlapExternalSamplingMCCFR,
    build_reachable_support,
    exact_nash_conv,
    exact_profile_value,
)
from test_external_hidden_discard_overlap import _overlap_worlds, _public_pre_r3_state


def _uniform_profile(rows):
    return {
        row.information_state_key: {
            action_key: 1.0 / len(row.action_keys) for action_key in row.action_keys
        }
        for row in rows
    }


def test_reachable_support_preserves_deliberate_nonroot_hidden_ambiguity() -> None:
    worlds = _overlap_worlds()
    state = _public_pre_r3_state()
    rows = build_reachable_support(state, worlds)
    assert rows
    assert any(
        len(row.concrete_states) > 1 and (row.round_index, row.actor) != (3, 0)
        for row in rows
    )
    p1_r3_ambiguous = [row for row in rows if row.round_index == 3 and row.actor == 1 and len(row.concrete_states) > 1]
    p0_r4_ambiguous = [row for row in rows if row.round_index == 4 and row.actor == 0 and len(row.concrete_states) > 1]
    assert p1_r3_ambiguous
    assert p0_r4_ambiguous


def test_uniform_profile_exact_br_and_nashconv_are_finite() -> None:
    worlds = _overlap_worlds()
    state = _public_pre_r3_state()
    rows = build_reachable_support(state, worlds)
    profile = _uniform_profile(rows)
    evaluation = exact_profile_value(state, worlds, profile=profile, support_rows=rows)
    nash = exact_nash_conv(state, worlds, profile=profile, support_rows=rows)
    assert math.isfinite(evaluation.expected_u0)
    assert math.isfinite(nash.br0.value)
    assert math.isfinite(nash.br1.value)
    assert nash.nash_conv >= 0.0
    assert math.isclose(nash.exploitability, 0.5 * nash.nash_conv, rel_tol=0.0, abs_tol=1e-12)


def test_overlap_mccfr_is_deterministic_for_fixed_seed() -> None:
    worlds = _overlap_worlds()
    state = _public_pre_r3_state()
    a = OverlapExternalSamplingMCCFR(state, worlds, seed=2026082897)
    b = OverlapExternalSamplingMCCFR(state, worlds, seed=2026082897)
    a.run(64)
    b.run(64)
    assert a.current_profile() == b.current_profile()
    assert a.snapshot() == b.snapshot()
    assert a.snapshot().iterations == 64
    assert a.snapshot().information_states > 0
    assert a.snapshot().terminal_evaluations > 0
    assert AUTHORITY.endswith("REDUCED_GAME_ONLY")
