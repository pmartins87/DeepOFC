import pytest

from deepofc.state import Card, OFCState, PendingPlacement, PlayerBoard, PlayerState, Row


def C(code: str) -> Card:
    return Card.from_code(code)


def fantasy_cards(count: int) -> tuple[Card, ...]:
    pool = tuple(
        C(code)
        for code in (
            "2s", "3s", "4s", "5s", "6s", "7s", "8s", "9s", "Ts",
            "Js", "Qs", "Ks", "As", "Ah", "Kh", "Qh", "JK1",
        )
    )
    return pool[:count]


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


def test_runtime_mode_is_one_joker_ultimate_variant_not_separate_joker_mode():
    with pytest.raises(ValueError, match="joker_ultimate"):
        OFCState(
            players=(PlayerState(chair=0), PlayerState(chair=1)),
            hero_chair=1,
            dealer_chair=1,
            acting_chair=1,
            round_index=0,
            mode="joker",
        )


def test_fantasy_is_state_inside_joker_ultimate_and_uses_round_minus_one():
    incoming = fantasy_cards(17)
    state = OFCState(
        players=(PlayerState(chair=0), PlayerState(chair=1, fantasy=True)),
        hero_chair=1,
        dealer_chair=1,
        acting_chair=1,
        round_index=-1,
        hero_incoming=incoming,
        hero_can_prepare=True,
        hero_can_confirm=True,
        action_required=True,
    )
    assert state.mode == "joker_ultimate"
    assert state.hero_is_fantasy
    assert len(state.hero_incoming) == 17


def test_fantasy_rejects_normal_round_index():
    with pytest.raises(ValueError, match="round_index=-1"):
        OFCState(
            players=(PlayerState(chair=0), PlayerState(chair=1, fantasy=True)),
            hero_chair=1,
            dealer_chair=1,
            acting_chair=1,
            round_index=0,
            hero_incoming=fantasy_cards(14),
        )


def test_fantasy_confirm_shape_is_exactly_13_placed_plus_1_to_4_unused():
    incoming = fantasy_cards(14)
    pending = tuple(
        [PendingPlacement(card, Row.TOP) for card in incoming[:3]]
        + [PendingPlacement(card, Row.MIDDLE) for card in incoming[3:8]]
        + [PendingPlacement(card, Row.BOTTOM) for card in incoming[8:13]]
    )
    state = OFCState(
        players=(PlayerState(chair=0), PlayerState(chair=1, fantasy=True)),
        hero_chair=1,
        dealer_chair=1,
        acting_chair=1,
        round_index=-1,
        hero_incoming=incoming,
        hero_pending=pending,
        hero_can_prepare=True,
        hero_can_confirm=True,
        action_required=True,
    )
    assert state.confirm_shape_is_legal()
    assert state.unassigned_incoming() == (incoming[-1],)


def test_fantasy_hidden_incoming_count_allows_14_to_17_only_for_fantasy_player():
    assert PlayerState(chair=0, fantasy=True, hidden_incoming_count=17).hidden_incoming_count == 17
    with pytest.raises(ValueError, match="normal-play"):
        PlayerState(chair=0, fantasy=False, hidden_incoming_count=17)
