from __future__ import annotations

from external_05g_counterfactual_weighted_completion import (
    SOURCE_LABEL,
    build_counterfactual_weighted_local_backward_completion,
)
from external_05g_uniform_backward_completion import build_uniform_local_backward_completion
from external_hidden_discard_overlap_strategic import build_reachable_support
from test_external_05g_uniform_backward_completion import four_world_fixture


def _unit_weights(support_rows):
    return {
        row.information_state_key: {repr(state): 1.0 for state in row.concrete_states}
        for row in support_rows
    }


def test_equal_positive_weights_exactly_reproduce_uniform_completion_choices() -> None:
    base, worlds = four_world_fixture()
    support = build_reachable_support(base, worlds)
    uniform = build_uniform_local_backward_completion(support)
    weighted = build_counterfactual_weighted_local_backward_completion(
        support,
        frozen_state_weights=_unit_weights(support),
        zero_weight_fallback_choices=uniform.choice_map(),
    )

    assert weighted.source_label == SOURCE_LABEL
    assert weighted.information_states == len(support)
    assert weighted.positive_weight_information_states == len(support)
    assert weighted.zero_weight_fallback_information_states == 0
    assert weighted.choice_map() == uniform.choice_map()
    assert weighted.policy_sha256 == uniform.policy_sha256


def test_all_zero_weights_retain_uniform_fallback_exactly() -> None:
    base, worlds = four_world_fixture()
    support = build_reachable_support(base, worlds)
    uniform = build_uniform_local_backward_completion(support)
    zero_weights = {
        row.information_state_key: {repr(state): 0.0 for state in row.concrete_states}
        for row in support
    }
    weighted = build_counterfactual_weighted_local_backward_completion(
        support,
        frozen_state_weights=zero_weights,
        zero_weight_fallback_choices=uniform.choice_map(),
    )

    assert weighted.choice_map() == uniform.choice_map()
    assert weighted.policy_sha256 == uniform.policy_sha256
    assert weighted.positive_weight_information_states == 0
    assert weighted.zero_weight_fallback_information_states == len(support)


def test_missing_state_weights_are_zero_and_cannot_create_illegal_choice() -> None:
    base, worlds = four_world_fixture()
    support = build_reachable_support(base, worlds)
    uniform = build_uniform_local_backward_completion(support)

    # Give exactly one concrete state positive mass per infoset. This exercises a
    # maximally concentrated valid posterior without relying on a strategic
    # expectation about whether any particular choice should change.
    concentrated = {
        row.information_state_key: {repr(row.concrete_states[0]): 1.0}
        for row in support
    }
    first = build_counterfactual_weighted_local_backward_completion(
        support,
        frozen_state_weights=concentrated,
        zero_weight_fallback_choices=uniform.choice_map(),
    )
    second = build_counterfactual_weighted_local_backward_completion(
        support,
        frozen_state_weights=concentrated,
        zero_weight_fallback_choices=uniform.choice_map(),
    )

    assert first.selected_actions == second.selected_actions
    assert first.policy_sha256 == second.policy_sha256
    for row in support:
        assert first.choice_map()[row.information_state_key] in row.action_keys


def test_weight_map_rejects_unknown_concrete_state_fingerprint() -> None:
    base, worlds = four_world_fixture()
    support = build_reachable_support(base, worlds)
    uniform = build_uniform_local_backward_completion(support)
    weights = _unit_weights(support)
    first_key = support[0].information_state_key
    weights[first_key]["not-a-real-state"] = 1.0

    try:
        build_counterfactual_weighted_local_backward_completion(
            support,
            frozen_state_weights=weights,
            zero_weight_fallback_choices=uniform.choice_map(),
        )
    except ValueError as exc:
        assert "non-support concrete state" in str(exc)
    else:
        raise AssertionError("unknown concrete-state fingerprint should fail closed")
