import pytest

from deepofc.actions import NormalPlacementAction
from deepofc.runtime_confirm import validate_normal_confirm_transition
from deepofc.runtime_plan import build_runtime_turn_plan
from deepofc.state import Card, OFCState, PendingPlacement, PlayerBoard, PlayerState, Row


def C(code: str) -> Card:
    return Card.from_code(code)


def before_confirm() -> OFCState:
    return OFCState(
        players=(
            PlayerState(chair=0, board=PlayerBoard(top=(C("2c"),))),
            PlayerState(
                chair=1,
                board=PlayerBoard(top=(C("As"),), middle=(C("Kh"),), bottom=(C("Qc"),)),
            ),
        ),
        hero_chair=1,
        dealer_chair=1,
        acting_chair=1,
        round_index=1,
        hero_incoming=(C("Jd"), C("Ts"), C("9h")),
        hero_pending=(
            PendingPlacement(C("Jd"), Row.TOP),
            PendingPlacement(C("Ts"), Row.MIDDLE),
        ),
        hero_can_prepare=True,
        hero_can_confirm=True,
        action_required=True,
    )


def action() -> NormalPlacementAction:
    return NormalPlacementAction(
        placements=(
            PendingPlacement(C("Jd"), Row.TOP),
            PendingPlacement(C("Ts"), Row.MIDDLE),
        ),
        discard=C("9h"),
    )


def same_round_after_confirm(*, acting=0, pending=None) -> OFCState:
    if pending is None:
        pending = (
            PendingPlacement(C("Jd"), Row.TOP),
            PendingPlacement(C("Ts"), Row.MIDDLE),
        )
    return OFCState(
        players=(
            PlayerState(chair=0, board=PlayerBoard(top=(C("2c"),))),
            PlayerState(
                chair=1,
                board=PlayerBoard(top=(C("As"),), middle=(C("Kh"),), bottom=(C("Qc"),)),
            ),
        ),
        hero_chair=1,
        dealer_chair=1,
        acting_chair=acting,
        round_index=1,
        hero_incoming=(C("Jd"), C("Ts"), C("9h")),
        hero_pending=tuple(pending),
        hero_can_prepare=False,
        hero_can_confirm=False,
        action_required=False,
    )


def next_round_after_confirm() -> OFCState:
    return OFCState(
        players=(
            # Opponent may already have changed before Hero receives the next
            # draw; the receipt intentionally does not require opponent board
            # immobility on the one-round-advanced evidence path.
            PlayerState(chair=0, board=PlayerBoard(top=(C("2c"), C("3c")))),
            PlayerState(
                chair=1,
                board=PlayerBoard(
                    top=(C("As"), C("Jd")),
                    middle=(C("Kh"), C("Ts")),
                    bottom=(C("Qc"),),
                ),
            ),
        ),
        hero_chair=1,
        dealer_chair=1,
        acting_chair=1,
        round_index=2,
        hero_incoming=(C("8d"), C("7h"), C("6s")),
        hero_discards=(C("9h"),),
        hero_can_prepare=True,
        hero_can_confirm=False,
        action_required=False,
    )


def test_same_round_handoff_proves_confirm_without_pretending_cards_are_committed():
    before = before_confirm()
    plan = build_runtime_turn_plan(before, action())
    receipt = validate_normal_confirm_transition(before, same_round_after_confirm(), plan)
    assert receipt.accepted
    assert receipt.transition == "same_round_handoff"
    assert receipt.previous_round == 1
    assert receipt.observed_round == 1


def test_direct_next_round_proves_exact_commit_and_discard():
    before = before_confirm()
    plan = build_runtime_turn_plan(before, action())
    receipt = validate_normal_confirm_transition(before, next_round_after_confirm(), plan)
    assert receipt.accepted
    assert receipt.transition == "next_round_committed"
    assert receipt.observed_round == 2


def test_confirm_is_not_accepted_if_hero_is_still_the_same_round_actor():
    before = before_confirm()
    plan = build_runtime_turn_plan(before, action())
    with pytest.raises(ValueError, match="still says Hero is acting"):
        validate_normal_confirm_transition(before, same_round_after_confirm(acting=1), plan)


def test_confirm_is_not_accepted_if_one_target_disappears_after_click():
    before = before_confirm()
    plan = build_runtime_turn_plan(before, action())
    wrong = same_round_after_confirm(
        pending=(PendingPlacement(C("Jd"), Row.TOP),)
    )
    with pytest.raises(ValueError, match="not preserved exactly"):
        validate_normal_confirm_transition(before, wrong, plan)


def test_fantasy_and_round_four_are_explicitly_out_of_scope():
    before = before_confirm()
    round4 = OFCState(
        players=before.players,
        hero_chair=before.hero_chair,
        dealer_chair=before.dealer_chair,
        acting_chair=before.acting_chair,
        round_index=4,
        hero_incoming=before.hero_incoming,
        hero_pending=before.hero_pending,
        hero_can_prepare=True,
        hero_can_confirm=True,
        action_required=True,
    )
    plan = build_runtime_turn_plan(round4, action())
    with pytest.raises(ValueError, match="rounds 0..3 only"):
        validate_normal_confirm_transition(round4, round4, plan)
