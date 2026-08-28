from __future__ import annotations

import math

from external_hidden_discard_overlap import find_hidden_discard_collisions, with_overlap_world
from external_hidden_discard_overlap_reach_audit import (
    AUTHORITY,
    audit_overlap_conditional_reach,
    summarize_overlap_reach,
)
from external_hidden_discard_overlap_strategic import build_reachable_support
from strategic_cfr import child_state, information_state_key, legal_action_pairs
from test_external_hidden_discard_overlap import _overlap_worlds, _public_pre_r3_state


def _uniform_profile(rows):
    return {
        row.information_state_key: {
            action_key: 1.0 / len(row.action_keys) for action_key in row.action_keys
        }
        for row in rows
    }


def test_uniform_profile_has_uniform_counterfactual_beliefs_on_constructed_overlap() -> None:
    worlds = _overlap_worlds()
    base = _public_pre_r3_state()
    rows = build_reachable_support(base, worlds)
    profile = _uniform_profile(rows)
    audit = audit_overlap_conditional_reach(base, worlds, support_rows=rows, profile=profile)
    assert audit.authority == AUTHORITY
    assert audit.ambiguous_information_states > 1
    ambiguous_defined = [
        row for row in audit.rows
        if row.compatible_states > 1 and row.uniform_vs_counterfactual_tv is not None
    ]
    assert ambiguous_defined
    assert max(row.uniform_vs_counterfactual_tv for row in ambiguous_defined) <= 1e-12
    summary = summarize_overlap_reach(audit)
    assert summary["ambiguous_information_states"] == audit.ambiguous_information_states


def test_private_type_dependent_root_policy_induces_nonuniform_opponent_counterfactual_belief() -> None:
    worlds = _overlap_worlds()
    base = _public_pre_r3_state()
    rows = build_reachable_support(base, worlds)
    profile = _uniform_profile(rows)
    witness = next(row for row in find_hidden_discard_collisions(base, worlds) if row.hidden_player == 0)
    world_by_id = {world.world_id: world for world in worlds}
    state_a = with_overlap_world(base, world_by_id[witness.world_a])
    root_key_a = information_state_key(state_a)
    matching = []
    for action_key, action in legal_action_pairs(state_a):
        child = child_state(state_a, action)
        if child.public_history[-1].placements == witness.public_placements:
            matching.append(action_key)
    assert matching
    chosen = sorted(matching)[0]
    profile[root_key_a] = {
        action_key: 1.0 if action_key == chosen else 0.0
        for action_key in profile[root_key_a]
    }

    audit = audit_overlap_conditional_reach(base, worlds, support_rows=rows, profile=profile)
    observer = next(row for row in audit.rows if row.information_state_key == witness.observer_information_state_key)
    assert observer.compatible_states >= 2
    assert observer.uniform_vs_counterfactual_tv is not None
    assert observer.uniform_vs_counterfactual_tv > 0.0
    assert math.isfinite(observer.uniform_vs_counterfactual_tv)
