from __future__ import annotations

import math

import pytest

from external_two_street_counterfactual_resolve import build_reachable_infoset_support
from external_two_street_reach_audit import AUTHORITY, audit_conditional_reach, summarize_reach_audit
from test_external_two_street_infoset_search import _coherent_r3_state, _support_worlds


def _uniform_complete_profile(support):
    return {
        row.information_state_key: {
            action_key: 1.0 / len(row.action_keys) for action_key in row.action_keys
        }
        for row in support
    }


def test_uniform_complete_profile_has_exact_root_uniform_reach_weights() -> None:
    worlds = _support_worlds()[:2]
    state = _coherent_r3_state(worlds[0])
    support = build_reachable_infoset_support(state, worlds)
    profile = _uniform_complete_profile(support)
    audit = audit_conditional_reach(state, worlds, profile=profile)
    assert audit.authority == AUTHORITY
    assert audit.information_states == len(support)
    root = next(
        row
        for row in audit.rows
        if row.round_index == 3 and row.actor == 0 and row.compatible_states == len(worlds)
    )
    assert math.isclose(root.uniform_vs_full_tv, 0.0, abs_tol=1e-12)
    assert math.isclose(root.uniform_vs_counterfactual_tv, 0.0, abs_tol=1e-12)
    assert math.isclose(root.full_vs_counterfactual_tv, 0.0, abs_tol=1e-12)
    summary = summarize_reach_audit(audit)
    assert summary["information_states"] == len(support)
    assert summary["multi_state_information_states"] >= 1


def test_reach_audit_fails_closed_on_incomplete_profile() -> None:
    worlds = _support_worlds()[:2]
    state = _coherent_r3_state(worlds[0])
    with pytest.raises(ValueError, match="explicit policy"):
        audit_conditional_reach(state, worlds, profile={})
