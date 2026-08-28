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


def _lexicographic_pure_complete_profile(support):
    profile = {}
    for row in support:
        chosen = min(row.action_keys)
        profile[row.information_state_key] = {
            action_key: 1.0 if action_key == chosen else 0.0
            for action_key in row.action_keys
        }
    return profile


def test_uniform_complete_profile_has_exact_root_uniform_reach_weights() -> None:
    worlds = _support_worlds()[:2]
    state = _coherent_r3_state(worlds[0])
    support = build_reachable_infoset_support(state, worlds)
    profile = _uniform_complete_profile(support)
    audit = audit_conditional_reach(state, worlds, profile=profile)
    assert audit.authority == AUTHORITY
    assert audit.information_states == len(support)
    assert audit.full_reach_defined_information_states == len(support)
    assert audit.counterfactual_reach_defined_information_states == len(support)
    root = next(
        row
        for row in audit.rows
        if row.round_index == 3 and row.actor == 0 and row.compatible_states == len(worlds)
    )
    assert root.full_reach_defined
    assert root.counterfactual_reach_defined
    assert math.isclose(root.uniform_vs_full_tv, 0.0, abs_tol=1e-12)
    assert math.isclose(root.uniform_vs_counterfactual_tv, 0.0, abs_tol=1e-12)
    assert math.isclose(root.full_vs_counterfactual_tv, 0.0, abs_tol=1e-12)
    summary = summarize_reach_audit(audit)
    assert summary["information_states"] == len(support)
    assert summary["multi_state_information_states"] >= 1


def test_zero_own_probability_branch_retains_counterfactual_reach() -> None:
    worlds = _support_worlds()[:2]
    state = _coherent_r3_state(worlds[0])
    support = build_reachable_infoset_support(state, worlds)
    profile = _lexicographic_pure_complete_profile(support)
    audit = audit_conditional_reach(state, worlds, profile=profile)

    # Full behavioral reach can be zero after the acting player deviated from
    # its own frozen pure strategy. Counterfactual reach deliberately removes
    # that own reach and therefore remains defined at some such states.
    off_policy_own_states = [
        row
        for row in audit.rows
        if not row.full_reach_defined and row.counterfactual_reach_defined
    ]
    assert off_policy_own_states
    assert audit.information_states == len(support)
    assert all(row.uniform_vs_full_tv is None for row in off_policy_own_states)
    assert all(row.uniform_vs_counterfactual_tv is not None for row in off_policy_own_states)


def test_reach_audit_fails_closed_on_incomplete_profile() -> None:
    worlds = _support_worlds()[:2]
    state = _coherent_r3_state(worlds[0])
    with pytest.raises(ValueError, match="explicit policy"):
        audit_conditional_reach(state, worlds, profile={})
