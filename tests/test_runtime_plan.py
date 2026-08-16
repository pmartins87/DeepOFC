import json

import pytest

from deepofc.actions import FantasyPlacementAction, NormalPlacementAction
from deepofc.runtime_plan import (
    RUNTIME_TURN_PLAN_SCHEMA_VERSION,
    build_runtime_turn_plan,
    strategic_decision_fingerprint,
)
from deepofc.state import Card, OFCState, PendingPlacement, PlayerBoard, PlayerState, Row


def C(code: str) -> Card:
    return Card.from_code(code)


def normal_state(*, pending=(), acting_chair: int = 1) -> OFCState:
    return OFCState(
        players=(
            PlayerState(
                chair=0,
                board=PlayerBoard(top=(C("2c"),), middle=(C("3c"),), bottom=(C("4c"),)),
            ),
            PlayerState(
                chair=1,
                board=PlayerBoard(top=(C("As"),), middle=(C("Kh"),), bottom=(C("Qc"),)),
            ),
        ),
        hero_chair=1,
        dealer_chair=1,
        acting_chair=acting_chair,
        round_index=1,
        hero_incoming=(C("Jd"), C("Ts"), C("9h")),
        hero_pending=tuple(pending),
        hero_can_prepare=True,
        # Deliberately false: planning must be possible before the UI exposes
        # Confirm after all required cards have been arranged.
        hero_can_confirm=False,
        action_required=False,
    )


def normal_action() -> NormalPlacementAction:
    return NormalPlacementAction(
        placements=(
            PendingPlacement(C("Jd"), Row.TOP),
            PendingPlacement(C("Ts"), Row.MIDDLE),
        ),
        discard=C("9h"),
    )


def fantasy_cards() -> tuple[Card, ...]:
    return tuple(
        C(code)
        for code in (
            "2s", "3s", "4s",
            "5s", "6s", "7s", "8s", "9s",
            "Ts", "Js", "Qs", "Ks", "As",
            "JK1",
        )
    )


def fantasy_state(*, pending=()) -> OFCState:
    return OFCState(
        players=(PlayerState(chair=0), PlayerState(chair=1, fantasy=True)),
        hero_chair=1,
        dealer_chair=1,
        acting_chair=1,
        round_index=-1,
        hero_incoming=fantasy_cards(),
        hero_pending=tuple(pending),
        hero_can_prepare=True,
        hero_can_confirm=False,
        action_required=False,
    )


def fantasy_action() -> FantasyPlacementAction:
    cards = fantasy_cards()
    placements = (
        *(PendingPlacement(card, Row.TOP) for card in cards[0:3]),
        *(PendingPlacement(card, Row.MIDDLE) for card in cards[3:8]),
        *(PendingPlacement(card, Row.BOTTOM) for card in cards[8:13]),
    )
    return FantasyPlacementAction(placements=placements, discards=(cards[13],))


def test_normal_plan_preserves_matching_pending_and_leaves_discard_loose():
    state = normal_state(pending=(PendingPlacement(C("Jd"), Row.TOP),))
    plan = build_runtime_turn_plan(state, normal_action())

    assert plan.schema_version == RUNTIME_TURN_PLAN_SCHEMA_VERSION
    assert plan.round_index == 1
    assert plan.fantasy is False
    assert [(p.card_code, p.row) for p in plan.already_correct] == [("Jd", Row.TOP)]
    assert [(p.card_code, p.row) for p in plan.placements_to_add] == [("Ts", Row.MIDDLE)]
    assert plan.unused_cards == ("9h",)
    assert plan.confirm_required is True


def test_decision_fingerprint_ignores_tentative_ui_progress():
    before = normal_state()
    after_one_matching_drag = normal_state(
        pending=(PendingPlacement(C("Jd"), Row.TOP),)
    )
    assert strategic_decision_fingerprint(before) == strategic_decision_fingerprint(
        after_one_matching_drag
    )


def test_wrong_row_pending_fails_closed_until_rearrangement_is_certified():
    state = normal_state(pending=(PendingPlacement(C("Jd"), Row.BOTTOM),))
    with pytest.raises(ValueError, match="strategy requires top"):
        build_runtime_turn_plan(state, normal_action())


def test_pending_card_that_strategy_wants_unused_fails_closed():
    state = normal_state(pending=(PendingPlacement(C("9h"), Row.TOP),))
    with pytest.raises(ValueError, match="must be unused"):
        build_runtime_turn_plan(state, normal_action())


def test_out_of_turn_plan_is_rejected_even_when_prearrangement_is_possible_in_ui():
    state = normal_state(acting_chair=0)
    with pytest.raises(ValueError, match="ordered acting chair"):
        build_runtime_turn_plan(state, normal_action())


def test_fantasy_plan_is_delta_only_and_never_embeds_screen_geometry():
    first = fantasy_cards()[0]
    state = fantasy_state(pending=(PendingPlacement(first, Row.TOP),))
    plan = build_runtime_turn_plan(state, fantasy_action())

    assert plan.fantasy is True
    assert plan.round_index == -1
    assert len(plan.target_placements) == 13
    assert len(plan.already_correct) == 1
    assert len(plan.placements_to_add) == 12
    assert plan.unused_cards == ("JK1",)

    payload = json.loads(plan.to_json())
    assert payload["schema_version"] == 1
    assert "source_rect" not in plan.to_json()
    assert "target_rect" not in plan.to_json()
    assert payload["unused_cards"] == ["JK1"]


def test_fingerprint_changes_when_strategy_relevant_opponent_board_changes():
    base = normal_state()
    changed = OFCState(
        players=(
            PlayerState(
                chair=0,
                board=PlayerBoard(top=(C("2d"),), middle=(C("3c"),), bottom=(C("4c"),)),
            ),
            base.player(1),
        ),
        hero_chair=base.hero_chair,
        dealer_chair=base.dealer_chair,
        acting_chair=base.acting_chair,
        round_index=base.round_index,
        hero_incoming=base.hero_incoming,
        hero_can_prepare=True,
    )
    assert strategic_decision_fingerprint(base) != strategic_decision_fingerprint(changed)
