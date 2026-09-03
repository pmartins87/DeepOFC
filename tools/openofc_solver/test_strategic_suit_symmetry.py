from __future__ import annotations

import random

from engine import Action, Card
from strategic_cfr import DealPlan, HUState, child_state, legal_action_pairs, sample_deal_plan
from strategic_suit_symmetry import (
    HUVisibleObservation,
    SuitCanonicalOutcomeSamplingMCCFR,
    canonical_action_pairs,
    canonical_information_key,
    canonical_node_view,
    canonical_visible_node_view,
    permute_card,
    visible_observation_from_state,
)


def _permute_packet(packet, suit_map):
    return tuple(sorted(permute_card(card, suit_map) for card in packet))


def _permute_plan(plan: DealPlan, suit_map) -> DealPlan:
    opening = (
        _permute_packet(plan.opening[0], suit_map),
        _permute_packet(plan.opening[1], suit_map),
    )
    rounds = tuple(
        (
            _permute_packet(packets[0], suit_map),
            _permute_packet(packets[1], suit_map),
        )
        for packets in plan.rounds
    )
    return DealPlan(opening=opening, rounds=rounds)  # type: ignore[arg-type]


def _mapped_action(
    action: Action,
    original_incoming,
    transformed_incoming,
    suit_map,
) -> Action:
    index_of = {card: i for i, card in enumerate(transformed_incoming)}
    placements = tuple(
        (
            index_of[permute_card(original_incoming[index], suit_map)],
            row,
        )
        for index, row in action.placements
    )
    discard = None
    if action.discard_index is not None:
        discard = index_of[
            permute_card(original_incoming[action.discard_index], suit_map)
        ]
    return Action(placements=placements, discard_index=discard)


def test_initial_infoset_and_action_set_are_suit_invariant() -> None:
    plan = sample_deal_plan(random.Random(7001))
    suit_map = (2, 0, 3, 1)
    transformed = _permute_plan(plan, suit_map)
    a = HUState(plan=plan)
    b = HUState(plan=transformed)
    key_a, map_a = canonical_information_key(a)
    key_b, map_b = canonical_information_key(b)
    assert key_a == key_b
    actions_a = {key for key, _ in canonical_action_pairs(a, map_a)}
    actions_b = {key for key, _ in canonical_action_pairs(b, map_b)}
    assert actions_a == actions_b
    assert len(actions_a) == 232


def test_public_history_is_canonicalized_with_cards() -> None:
    plan = sample_deal_plan(random.Random(7002))
    suit_map = (1, 3, 0, 2)
    tplan = _permute_plan(plan, suit_map)
    a = HUState(plan=plan)
    b = HUState(plan=tplan)

    # Non-dealer opening.
    _akey, action_a = legal_action_pairs(a)[37]
    incoming_a = a.plan.incoming(0, 0)
    incoming_b = b.plan.incoming(0, 0)
    action_b = _mapped_action(action_a, incoming_a, incoming_b, suit_map)
    a = child_state(a, action_a)
    b = child_state(b, action_b)
    assert canonical_information_key(a)[0] == canonical_information_key(b)[0]

    # Dealer opening.  This checks a history containing both players.
    _akey, action_a = legal_action_pairs(a)[81]
    incoming_a = a.plan.incoming(0, 1)
    incoming_b = b.plan.incoming(0, 1)
    action_b = _mapped_action(action_a, incoming_a, incoming_b, suit_map)
    a = child_state(a, action_a)
    b = child_state(b, action_b)
    assert canonical_information_key(a)[0] == canonical_information_key(b)[0]


def test_node_view_is_deterministic() -> None:
    state = HUState(plan=sample_deal_plan(random.Random(7003)))
    k1, p1, m1 = canonical_node_view(state)
    k2, p2, m2 = canonical_node_view(state)
    assert k1 == k2 and m1 == m2
    assert [x for x, _ in p1] == [x for x, _ in p2]


def test_visible_only_node_view_matches_full_state_wrapper() -> None:
    state = HUState(plan=sample_deal_plan(random.Random(7005)))
    while not state.terminal():
        visible = visible_observation_from_state(state)
        full_key, full_pairs, full_map = canonical_node_view(state)
        visible_key, visible_pairs, visible_map = canonical_visible_node_view(visible)
        assert visible_key == full_key
        assert visible_map == full_map
        assert [key for key, _action in visible_pairs] == [
            key for key, _action in full_pairs
        ]
        state = child_state(state, full_pairs[len(full_pairs) // 3][1])


def _swap_hidden_future_cards(plan: DealPlan) -> DealPlan:
    rounds = [[list(packet) for packet in pair] for pair in plan.rounds]
    rounds[0][1][0], rounds[3][0][0] = rounds[3][0][0], rounds[0][1][0]
    return DealPlan(
        opening=plan.opening,
        rounds=tuple(
            (tuple(sorted(pair[0])), tuple(sorted(pair[1])))
            for pair in rounds
        ),  # type: ignore[arg-type]
    )


def test_hidden_opponent_and_future_cards_cannot_change_runtime_node() -> None:
    plan_a = sample_deal_plan(random.Random(7006))
    plan_b = _swap_hidden_future_cards(plan_a)
    state_a = HUState(plan=plan_a)
    state_b = HUState(plan=plan_b)

    # At the root, actor 0 sees only its own opening packet.  Actor 1's packet
    # and every future packet can differ without changing key or legal actions.
    view_a = canonical_visible_node_view(visible_observation_from_state(state_a))
    view_b = canonical_visible_node_view(visible_observation_from_state(state_b))
    assert view_a[0] == view_b[0]
    assert [key for key, _ in view_a[1]] == [key for key, _ in view_b[1]]

    # After the same public opening placement, actor 1 sees its own unchanged
    # opening packet; the altered future cards remain outside the boundary.
    action = legal_action_pairs(state_a)[29][1]
    state_a = child_state(state_a, action)
    state_b = child_state(state_b, action)
    view_a = canonical_visible_node_view(visible_observation_from_state(state_a))
    view_b = canonical_visible_node_view(visible_observation_from_state(state_b))
    assert view_a[0] == view_b[0]
    assert [key for key, _ in view_a[1]] == [key for key, _ in view_b[1]]


def test_visible_boundary_rejects_incomplete_public_history() -> None:
    state = HUState(plan=sample_deal_plan(random.Random(7007)))
    state = child_state(state, legal_action_pairs(state)[0][1])
    visible = HUVisibleObservation.from_state(state)
    malformed = HUVisibleObservation(
        round_index=visible.round_index,
        actor=visible.actor,
        boards=visible.boards,
        own_discards=visible.own_discards,
        incoming=visible.incoming,
        public_history=(),
    )
    try:
        canonical_visible_node_view(malformed)
    except ValueError as exc:
        assert "complete nondealer/dealer action prefix" in str(exc)
    else:
        raise AssertionError("incomplete public history must fail closed")


def test_suit_canonical_mccfr_smoke() -> None:
    solver = SuitCanonicalOutcomeSamplingMCCFR(
        seed=7004, epsilon=0.6, cfr_plus=True
    )
    stats = solver.run(3)
    assert stats.iterations == 3
    assert stats.episodes == 6
    assert stats.max_actions == 232
    assert stats.infosets > 0
    for node in solver.nodes.values():
        assert abs(sum(node.average_policy()) - 1.0) < 1e-9


def main() -> None:
    test_initial_infoset_and_action_set_are_suit_invariant()
    test_public_history_is_canonicalized_with_cards()
    test_node_view_is_deterministic()
    test_visible_only_node_view_matches_full_state_wrapper()
    test_hidden_opponent_and_future_cards_cannot_change_runtime_node()
    test_visible_boundary_rejects_incomplete_public_history()
    test_suit_canonical_mccfr_smoke()
    print("OPENOFC_STRATEGIC_SUIT_SYMMETRY_TEST=PASS")


if __name__ == "__main__":
    main()
