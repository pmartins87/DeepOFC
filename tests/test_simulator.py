from deepofc.actions import NormalPlacementAction, FantasyPlacementAction
from deepofc.scoring import HandCategory, completed_board_ranks
from deepofc.simulator import (
    PHYSICAL_DECK_54,
    DeterministicDeck,
    apply_fantasy_action,
    apply_normal_action,
    normal_fantasy_entry_cards,
    refantasy_qualifies,
    remaining_physical_cards,
    settle_raw_points,
)
from deepofc.state import Card, PendingPlacement, PlayerBoard, Row


def C(code: str) -> Card:
    return Card.from_code(code)


def P(code: str, row: Row) -> PendingPlacement:
    return PendingPlacement(card=C(code), row=row)


def test_physical_deck_is_54_unique_cards_with_two_persistent_jokers():
    assert len(PHYSICAL_DECK_54) == 54
    assert len(set(PHYSICAL_DECK_54)) == 54
    assert C("JK1") in PHYSICAL_DECK_54
    assert C("JK2") in PHYSICAL_DECK_54


def test_seeded_deck_is_reproducible_and_draw_is_immutable():
    a = DeterministicDeck.shuffled(123)
    b = DeterministicDeck.shuffled(123)
    assert a.cards == b.cards
    first, a2 = a.draw(5)
    assert len(first) == 5
    assert a.cursor == 0
    assert a2.cursor == 5
    assert a2.remaining_count == 49


def test_remaining_cards_excludes_known_physical_identity_not_joker_nominals():
    known = (C("As"), C("Ah"), C("JK1"))
    remaining = remaining_physical_cards(known)
    assert len(remaining) == 51
    assert C("As") not in remaining
    assert C("Ah") not in remaining
    assert C("JK1") not in remaining
    assert C("JK2") in remaining


def test_apply_round_zero_places_all_five_without_discard():
    incoming = (C("As"), C("Kh"), C("Qc"), C("Jd"), C("Ts"))
    action = NormalPlacementAction(
        placements=(
            P("As", Row.TOP),
            P("Kh", Row.TOP),
            P("Qc", Row.MIDDLE),
            P("Jd", Row.MIDDLE),
            P("Ts", Row.BOTTOM),
        )
    )
    board, discards = apply_normal_action(
        PlayerBoard(), action, round_index=0, incoming=incoming
    )
    assert board.filled_count() == 5
    assert discards == ()
    assert set(board.top) == {C("As"), C("Kh")}


def test_apply_later_round_places_two_and_returns_exact_discard():
    board = PlayerBoard(
        top=(C("As"), C("Kh")),
        middle=(C("Qc"), C("Jd"), C("Ts")),
        bottom=(C("9s"), C("8s"), C("7s"), C("6s")),
    )
    incoming = (C("5s"), C("4h"), C("3c"))
    action = NormalPlacementAction(
        placements=(P("5s", Row.BOTTOM), P("4h", Row.MIDDLE)),
        discard=C("3c"),
    )
    new_board, discards = apply_normal_action(
        board, action, round_index=4, incoming=incoming
    )
    assert new_board.is_complete()
    assert discards == (C("3c"),)


def test_apply_fantasy_materializes_board_and_unused_cards():
    action = FantasyPlacementAction(
        placements=(
            P("Qs", Row.TOP), P("Qh", Row.TOP), P("2c", Row.TOP),
            P("9s", Row.MIDDLE), P("9h", Row.MIDDLE), P("8c", Row.MIDDLE), P("7d", Row.MIDDLE), P("6c", Row.MIDDLE),
            P("As", Row.BOTTOM), P("Ks", Row.BOTTOM), P("Js", Row.BOTTOM), P("Ts", Row.BOTTOM), P("5s", Row.BOTTOM),
        ),
        discards=(C("3d"), C("4h")),
    )
    board, discards = apply_fantasy_action(action)
    assert board.is_complete()
    assert discards == (C("3d"), C("4h"))


def test_hu_raw_settlement_is_antisymmetric():
    a = PlayerBoard(
        top=(C("Qs"), C("Qh"), C("2c")),
        middle=(C("9s"), C("9h"), C("8c"), C("7d"), C("6c")),
        bottom=(C("As"), C("Ks"), C("Js"), C("Ts"), C("5s")),
    )
    b = PlayerBoard(
        top=(C("Js"), C("Jh"), C("3c")),
        middle=(C("8s"), C("8h"), C("7c"), C("6d"), C("5c")),
        bottom=(C("Ad"), C("Kd"), C("Qd"), C("Td"), C("9d")),
    )
    result = settle_raw_points((a, b))
    assert result.points_by_chair[0] == -result.points_by_chair[1]
    assert result.zero_sum


def test_three_player_raw_settlement_remains_zero_sum():
    boards = (
        PlayerBoard(
            top=(C("Qs"), C("Qh"), C("2c")),
            middle=(C("9s"), C("9h"), C("8c"), C("7d"), C("6c")),
            bottom=(C("As"), C("Ks"), C("Js"), C("Ts"), C("5s")),
        ),
        PlayerBoard(
            top=(C("Jc"), C("Jh"), C("3c")),
            middle=(C("8s"), C("8h"), C("7c"), C("6d"), C("5c")),
            bottom=(C("Ad"), C("Kd"), C("Qd"), C("Td"), C("9d")),
        ),
        PlayerBoard(
            top=(C("Tc"), C("Th"), C("4c")),
            middle=(C("7s"), C("7h"), C("6h"), C("5h"), C("4h")),
            bottom=(C("Ac"), C("Kc"), C("Qc"), C("Jd"), C("9c")),
        ),
    )
    result = settle_raw_points(boards)
    assert result.zero_sum
    assert sum(result.points_by_chair) == 0


def test_progressive_normal_fantasy_entry_counts():
    def board_with_top(top):
        return PlayerBoard(
            top=top,
            middle=(C("2s"), C("3h"), C("4c"), C("5d"), C("7s")),
            bottom=(C("9s"), C("Ts"), C("Js"), C("Qs"), C("Ks")),
        )

    assert normal_fantasy_entry_cards(board_with_top((C("Qh"), C("Qd"), C("8c")))) == 14
    assert normal_fantasy_entry_cards(board_with_top((C("Kh"), C("Kd"), C("8c")))) == 15
    assert normal_fantasy_entry_cards(board_with_top((C("Ah"), C("Ad"), C("8c")))) == 16
    assert normal_fantasy_entry_cards(board_with_top((C("8h"), C("8d"), C("8c")))) == 17


def test_refantasy_predicate_accepts_top_trips_or_bottom_quads_plus():
    top_trips = PlayerBoard(
        top=(C("7s"), C("7h"), C("7d")),
        middle=(C("8s"), C("8h"), C("6c"), C("5d"), C("4c")),
        bottom=(C("As"), C("Ks"), C("Qs"), C("Js"), C("Ts")),
    )
    assert refantasy_qualifies(top_trips)

    bottom_quads = PlayerBoard(
        top=(C("Ah"), C("Kd"), C("6c")),
        middle=(C("9s"), C("9h"), C("8c"), C("7d"), C("5c")),
        bottom=(C("Qs"), C("Qh"), C("Qd"), C("Qc"), C("As")),
    )
    assert refantasy_qualifies(bottom_quads)
    _, _, rank = completed_board_ranks(bottom_quads)
    assert rank.category == HandCategory.QUADS
