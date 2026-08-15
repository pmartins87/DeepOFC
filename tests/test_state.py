import pytest

from deepofc.state import Card, OFCState, PendingPlacement, PlayerBoard, PlayerState, Row


def C(code: str) -> Card:
    return Card.from_code(code)


def test_standard_and_joker_cards_are_distinct_physical_cards():
    cards = {C("As"), C("Ah"), C("JK1"), C("JK2")}
    assert len(cards) == 4
    assert {c.code for c in cards} == {"As", "Ah", "JK1", "JK2"}


def test_duplicate_known_card_is_rejected():
    ace = C("As")
    p0 = PlayerState(chair=0, board=PlayerBoard(top=(ace,)))
    p1 = PlayerState(chair=1)
    with pytest.raises(ValueError, match="duplicate physical card"):
        OFCState(
            players=(p0, p1),
            hero_chair=0,
            dealer_chair=1,
            acting_chair=0,
            round_index=0,
            hero_incoming=(ace,),
            hero_can_confirm=True,
        )


def test_board_capacity_is_3_5_5():
    board = PlayerBoard(
        top=(C("As"), C("Ks"), C("Qs")),
        middle=(C("Js"), C("Ts"), C("9s"), C("8s"), C("7s")),
        bottom=(C("6s"), C("5s"), C("4s"), C("3s"), C("2s")),
    )
    assert board.filled_count() == 13
    assert board.is_complete()


def test_only_two_or_three_players_supported():
    with pytest.raises(ValueError, match="2 or 3 players"):
        OFCState(
            players=(PlayerState(chair=0),),
            hero_chair=0,
            dealer_chair=0,
            acting_chair=0,
            round_index=0,
        )


def test_pending_placements_are_row_membership_not_persistent_slots():
    hero = PlayerState(
        chair=1,
        board=PlayerBoard(
            top=(C("Ks"), C("4h")),
            middle=(C("8c"), C("5c")),
            bottom=(C("Ah"), C("Th"), C("9h"), C("7h"), C("6h")),
        ),
    )
    opp = PlayerState(chair=0)
    state = OFCState(
        players=(opp, hero),
        hero_chair=1,
        dealer_chair=1,
        acting_chair=1,
        round_index=3,
        hero_incoming=(C("Qc"), C("Ts"), C("Jh")),
        hero_pending=(
            PendingPlacement(C("Jh"), Row.TOP),
            PendingPlacement(C("Qc"), Row.MIDDLE),
        ),
        hero_can_prepare=True,
        hero_can_confirm=True,
        action_required=True,
    )
    assert state.unassigned_incoming() == (C("Ts"),)
    assert state.confirm_shape_is_legal()


def test_cannot_confirm_when_opponent_is_acting():
    with pytest.raises(ValueError, match="acting chair"):
        OFCState(
            players=(PlayerState(chair=0), PlayerState(chair=1)),
            hero_chair=1,
            dealer_chair=1,
            acting_chair=0,
            round_index=0,
            hero_can_prepare=True,
            hero_can_confirm=True,
        )
