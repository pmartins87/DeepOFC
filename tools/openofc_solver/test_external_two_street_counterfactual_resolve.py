from __future__ import annotations

import math

import pytest

from external_two_street_counterfactual_resolve import (
    AUTHORITY,
    build_reachable_infoset_support,
    complete_profile_with_counterfactual_resolve,
    exact_profile_value_strict,
    resolve_missing_infoset,
)
from external_two_street_infoset_search import run_two_street_infoset_uct
from external_two_street_mccfr import visit_profile_from_search
from test_external_two_street_infoset_search import _coherent_r3_state, _support_worlds


def test_reachable_support_is_deterministic_and_root_hidden_blind() -> None:
    worlds = _support_worlds()[:2]
    state = _coherent_r3_state(worlds[0])
    a = build_reachable_infoset_support(state, worlds)
    b = build_reachable_infoset_support(state, tuple(reversed(worlds)))
    assert a == b
    assert len(a) > 4
    roots = [row for row in a if row.round_index == 3 and row.actor == 0]
    root_key = next(row.information_state_key for row in roots if len(row.concrete_states) == len(worlds))
    root = next(row for row in a if row.information_state_key == root_key)
    assert len(root.concrete_states) == 2
    assert len(root.action_keys) > 1


def test_local_resolver_is_deterministic_and_visits_every_root_action() -> None:
    worlds = _support_worlds()[:2]
    state = _coherent_r3_state(worlds[0])
    support = build_reachable_infoset_support(state, worlds)
    root = next(
        row
        for row in support
        if row.round_index == 3 and row.actor == 0 and len(row.concrete_states) == len(worlds)
    )
    iterations = max(64, len(root.action_keys))
    a = resolve_missing_infoset(
        root,
        frozen_p0_profile={},
        frozen_p1_profile={},
        iterations=iterations,
        seed=2026082861,
        exploration=1.0,
    )
    b = resolve_missing_infoset(
        root,
        frozen_p0_profile={},
        frozen_p1_profile={},
        iterations=iterations,
        seed=2026082861,
        exploration=1.0,
    )
    assert a == b
    assert a.actor == 0
    assert all(visits > 0 for _key, visits in a.action_visits)
    assert math.isclose(sum(probability for _key, probability in a.distribution), 1.0)
    with pytest.raises(ValueError, match="cover every legal root action"):
        resolve_missing_infoset(
            root,
            frozen_p0_profile={},
            frozen_p1_profile={},
            iterations=len(root.action_keys) - 1,
            seed=1,
        )


def test_completion_eliminates_uniform_unseen_infoset_fallback_for_strict_eval() -> None:
    worlds = _support_worlds()[:2]
    state = _coherent_r3_state(worlds[0])
    search = run_two_street_infoset_uct(
        state,
        worlds,
        iterations=128,
        seed=2026082863,
        exploration=1.0,
    )
    base = visit_profile_from_search(search)
    support = build_reachable_infoset_support(state, worlds)
    assert len(base) < len(support)
    with pytest.raises(ValueError, match="strict profile evaluation refuses unseen infosets"):
        exact_profile_value_strict(
            state,
            worlds,
            support_rows=support,
            p0_profile=base,
            p1_profile=base,
        )

    iterations = max(64, max(len(row.action_keys) for row in support))
    completed = complete_profile_with_counterfactual_resolve(
        base,
        support,
        iterations_per_infoset=iterations,
        seed=2026082867,
        exploration=1.0,
    )
    assert completed.authority == AUTHORITY
    assert completed.completed_information_states == completed.reachable_information_states
    assert completed.resolved_information_states > 0
    result = exact_profile_value_strict(
        state,
        worlds,
        support_rows=support,
        p0_profile=completed.profile,
        p1_profile=completed.profile,
    )
    assert math.isfinite(result.expected_u0)
    assert result.information_states_seen == len(support)
