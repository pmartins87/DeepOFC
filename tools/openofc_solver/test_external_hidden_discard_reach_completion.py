from __future__ import annotations

import math

from external_hidden_discard_overlap import find_hidden_discard_collisions, with_overlap_world
from external_hidden_discard_overlap_reach_audit import audit_overlap_conditional_reach
from external_hidden_discard_overlap_strategic import build_reachable_support
from external_hidden_discard_reach_completion import (
    AUTHORITY,
    build_counterfactual_priors,
    complete_with_counterfactual_priors,
)
from strategic_cfr import child_state, information_state_key, legal_action_pairs
from test_external_hidden_discard_overlap import _overlap_worlds, _public_pre_r3_state


def _uniform_profile(rows):
    return {
        row.information_state_key: {
            action_key: 1.0 / len(row.action_keys) for action_key in row.action_keys
        }
        for row in rows
    }


def _skewed_complete_profile(base, worlds, rows):
    profile = _uniform_profile(rows)
    witness = next(row for row in find_hidden_discard_collisions(base, worlds) if row.hidden_player == 0)
    by_id = {world.world_id: world for world in worlds}
    state_a = with_overlap_world(base, by_id[witness.world_a])
    state_b = with_overlap_world(base, by_id[witness.world_b])

    def action_for_public(state, placements):
        matches = []
        for action_key, action in legal_action_pairs(state):
            if child_state(state, action).public_history[-1].placements == placements:
                matches.append(action_key)
        assert matches
        return sorted(matches)[0]

    desired_a = action_for_public(state_a, witness.public_placements)
    root_a = information_state_key(state_a)
    profile[root_a] = {
        action_key: 1.0 if action_key == desired_a else 0.0
        for action_key in profile[root_a]
    }

    root_b = information_state_key(state_b)
    alternative_b = next(
        action_key
        for action_key, action in legal_action_pairs(state_b)
        if child_state(state_b, action).public_history[-1].placements != witness.public_placements
    )
    profile[root_b] = {
        action_key: 1.0 if action_key == alternative_b else 0.0
        for action_key in profile[root_b]
    }
    return profile, witness


def test_counterfactual_prior_matches_independent_reach_audit_on_skewed_collision() -> None:
    worlds = _overlap_worlds()
    base = _public_pre_r3_state()
    rows = build_reachable_support(base, worlds)
    profile, witness = _skewed_complete_profile(base, worlds, rows)
    priors = build_counterfactual_priors(
        base, worlds, support_rows=rows, reference_profile=profile
    )
    prior = next(row for row in priors if row.information_state_key == witness.observer_information_state_key)
    assert prior.compatible_states == 2
    assert prior.positive_states == 1
    assert not prior.zero_counterfactual_mass
    assert math.isclose(prior.uniform_tv, 0.5, rel_tol=0.0, abs_tol=1e-12)

    audit = audit_overlap_conditional_reach(base, worlds, support_rows=rows, profile=profile)
    audit_row = next(row for row in audit.rows if row.information_state_key == witness.observer_information_state_key)
    assert math.isclose(
        float(prior.uniform_tv),
        float(audit_row.uniform_vs_counterfactual_tv),
        rel_tol=0.0,
        abs_tol=1e-12,
    )


def test_one_missing_infoset_completion_is_deterministic_and_preserves_observed_policy() -> None:
    worlds = _overlap_worlds()
    base = _public_pre_r3_state()
    rows = build_reachable_support(base, worlds)
    reference, witness = _skewed_complete_profile(base, worlds, rows)
    priors = build_counterfactual_priors(
        base, worlds, support_rows=rows, reference_profile=reference
    )
    missing_key = witness.observer_information_state_key
    original = {key: dict(dist) for key, dist in reference.items() if key != missing_key}
    kwargs = dict(
        reference_profile=reference,
        priors=priors,
        iterations_per_resolved_infoset=64,
        seed=2026082921,
        exploration=1.0,
    )
    a = complete_with_counterfactual_priors(original, rows, **kwargs)
    b = complete_with_counterfactual_priors(original, rows, **kwargs)
    assert a == b
    assert a.authority == AUTHORITY
    assert a.resolved_information_states == 1
    assert a.positive_counterfactual_resolutions == 1
    assert a.zero_counterfactual_fallback_resolutions == 0
    assert missing_key in a.profile
    for key, distribution in original.items():
        assert a.profile[key] == distribution
    assert math.isclose(sum(a.profile[missing_key].values()), 1.0, rel_tol=0.0, abs_tol=1e-12)
