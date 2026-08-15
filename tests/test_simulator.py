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
    # Round 4 begins with 11 committed cards and exactly two row slots free.
    board = PlayerBoard(
        top=(C("As"), C("Kh")),
        middle=(C("Qc"), C("Jd"), C("Ts"), C("4c")),
        bottom=(C("9s"), C("8s"), C("7s"), C("6s"), C("5s")),
    )
    incoming = (C("Qh"), C("4h"), C("3c"))
    action = NormalPlacementAction(
        placements=(P("Qh", Row.TOP), P("4h", Row.MIDDLE)),
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
            P("6s", Row.TOP), P("6h", Row.TOP), P("2c", Row.TOP),
            P("9s", Row.MIDDLE), P("9h", Row.MIDDLE), P("8c", Row.MIDDLE), P("7d", Row.MIDDLE), P("6c", Row.MIDDLE),
            P("As", Row.BOTTOM), P("Ks", Row.BOTTOM), P("Js", Row.BOTTOM), P("Ts", Row.BOTTOM), P("5s", Row.BOTTOM),
        ),
        discards=(C("3d"), C("4h")),
    )
    board, discards = apply_fantasy_action(action)
    assert board.is_complete()
    assert discards == (C("3d"), C("4h"))


def _valid_board_a() -> PlayerBoard:
    return PlayerBoard(
        top=(C("6s"), C("6h"), C("2c")),
        middle=(C("9s"), C("9h"), C("8c"), C("7d"), C("6c")),
        bottom=(C("As"), C("Ks"), C("Js"), C("Ts"), C("5s")),
    )


def _valid_board_b() -> PlayerBoard:
    return PlayerBoard(
        top=(C("5c"), C("5d"), C("3c")),
        middle=(C("8s"), C("8h"), C("7c"), C("6d"), C("4c")),
        bottom=(C("Ad"), C("Kd"), C("Qd"), C("Td"), C("9d")),
    )


def test_hu_raw_settlement_is_antisymmetric():
    result = settle_raw_points((_valid_board_a(), _valid_board_b()))
    assert result.points_by_chair[0] == -result.points_by_chair[1]
    assert result.zero_sum


def test_three_player_raw_settlement_remains_zero_sum():
    c = PlayerBoard(
        top=(C("4s"), C("4h"), C("3d")),
        middle=(C("7s"), C("7h"), C("6h"), C("5h"), C("4d")),
        bottom=(C("Ac"), C("Kc"), C("Qc"), C("Jc"), C("9c")),
    )
    result = settle_raw_points((_valid_board_a(), _valid_board_b(), c))
    assert result.zero_sum
    assert sum(result.points_by_chair) == 0


def test_progressive_normal_fantasy_entry_counts():
    def board_with_top(top):
        # Middle straight is stronger than every qualifying Top pair/trips;
        # Bottom straight flush is stronger than Middle, so the board is valid.
        return PlayerBoard(
            top=top,
            middle=(C("3c"), C("4d"), C("5h"), C("6s"), C("7c")),
            bottom=(C("9s"), C("Ts"), C("Js"), C("Qs"), C("Ks")),
        )

    assert normal_fantasy_entry_cards(board_with_top((C("Qh"), C("Qd"), C("2h")))) == 14
    assert normal_fantasy_entry_cards(board_with_top((C("Kh"), C("Kd"), C("2h")))) == 15
    assert normal_fantasy_entry_cards(board_with_top((C("Ah"), C("Ad"), C("2h")))) == 16
    assert normal_fantasy_entry_cards(board_with_top((C("8h"), C("8d"), C("8c")))) == 17


def test_refantasy_predicate_accepts_top_trips_or_bottom_quads_plus():
    top_trips = PlayerBoard(
        top=(C("8s"), C("8h"), C("8d")),
        middle=(C("3c"), C("4d"), C("5h"), C("6s"), C("7c")),
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
