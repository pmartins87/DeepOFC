from __future__ import annotations

import math
import pytest

from external_two_street_infoset_search import run_two_street_infoset_uct
from external_two_street_mccfr import (
    AUTHORITY,
    TwoStreetExternalSamplingMCCFR,
    exact_profile_value,
    root_total_variation,
    visit_profile_from_search,
)
from strategic_cfr import information_state_key, legal_action_pairs
from test_external_two_street_infoset_search import _coherent_r3_state, _support_worlds


def test_mccfr_current_profile_is_deterministic_and_legal() -> None:
    worlds = _support_worlds()
    state = _coherent_r3_state(worlds[0])
    a = TwoStreetExternalSamplingMCCFR(state, worlds, seed=2026082853)
    b = TwoStreetExternalSamplingMCCFR(state, worlds, seed=2026082853)
    a.run(24)
    b.run(24)
    assert a.snapshot() == b.snapshot()
    assert a.current_profile() == b.current_profile()
    assert a.regrets == b.regrets
    assert a.snapshot().root_information_state_key == information_state_key(state)
    for distribution in a.current_profile().values():
        assert math.isclose(sum(distribution.values()), 1.0, abs_tol=1e-12)
        assert all(probability >= 0.0 for probability in distribution.values())


def test_exact_fixed_profile_evaluator_and_search_profile_are_coherent() -> None:
    worlds = _support_worlds()[:2]
    state = _coherent_r3_state(worlds[0])
    search = run_two_street_infoset_uct(
        state, worlds, iterations=100, seed=2026082857, exploration=1.0
    )
    search_profile = visit_profile_from_search(search)
    root_key = information_state_key(state)
    assert root_key in search_profile
    assert math.isclose(sum(search_profile[root_key].values()), 1.0, abs_tol=1e-12)

    uniform = exact_profile_value(state, worlds, p0_profile={}, p1_profile={})
    repeated = exact_profile_value(state, worlds, p0_profile={}, p1_profile={})
    assert uniform == repeated
    assert math.isfinite(uniform.expected_u0)
    assert uniform.terminal_leaves > 0

    tv = root_total_variation(state, search_profile, {})
    assert 0.0 <= tv <= 1.0


def test_mccfr_validation_fails_closed() -> None:
    worlds = _support_worlds()
    state = _coherent_r3_state(worlds[0])
    with pytest.raises(ValueError, match="at least two"):
        TwoStreetExternalSamplingMCCFR(state, worlds[:1], seed=1)
    trainer = TwoStreetExternalSamplingMCCFR(state, worlds, seed=1)
    with pytest.raises(ValueError, match="non-negative"):
        trainer.run(-1)
    action_keys = tuple(key for key, _action in legal_action_pairs(state))
    bad = {information_state_key(state): {"not-a-legal-action": 1.0}}
    with pytest.raises(ValueError, match="illegal actions"):
        exact_profile_value(state, worlds[:2], p0_profile=bad, p1_profile={})
    assert action_keys
