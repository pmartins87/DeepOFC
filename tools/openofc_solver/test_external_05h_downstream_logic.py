from __future__ import annotations

from external_05g_uniform_backward_completion import build_uniform_local_backward_completion
from external_hidden_discard_overlap_strategic import build_reachable_support
from run_external_05g_q1b import _materialize_completion_profile
from run_external_05h_h2 import MCCFR_NATIVE, _assemble_m
from run_external_05h_h3 import _band
from test_external_05g_uniform_backward_completion import four_world_fixture


def test_h2_mccfr_native_overrides_completion_only_at_native_keys() -> None:
    base, worlds = four_world_fixture()
    support = build_reachable_support(base, worlds)
    completion = build_uniform_local_backward_completion(support)
    completion_profile = _materialize_completion_profile(support, completion.choice_map())

    row = support[0]
    keys = tuple(row.action_keys)
    assert len(keys) >= 2
    native_dist = {key: 0.0 for key in keys}
    native_dist[keys[-1]] = 1.0
    native = {row.information_state_key: native_dist}

    m_profile, source_map = _assemble_m(
        support_rows=support,
        mccfr=native,
        completion=completion_profile,
    )

    assert set(m_profile) == {item.information_state_key for item in support}
    assert set(source_map) == set(m_profile)
    assert source_map[row.information_state_key] == MCCFR_NATIVE
    assert m_profile[row.information_state_key] == native_dist

    for other in support[1:]:
        key = other.information_state_key
        assert source_map[key] != MCCFR_NATIVE
        assert m_profile[key] == completion_profile[key]


def test_h3_interpretation_band_boundaries_are_frozen() -> None:
    assert _band(0.0) == "NEAR_NASH_STRICT"
    assert _band(1e-12) == "NEAR_NASH_STRICT"
    assert _band(1e-6) == "NEAR_NASH_STRICT"
    assert _band(1.0000001e-6) == "LOW_BUT_NOT_STRICT"
    assert _band(1e-3) == "LOW_BUT_NOT_STRICT"
    assert _band(1.0000001e-3) == "MATERIAL_EXPLOITABILITY"
