import pytest

from deepofc.state import Card, OFCState, PlayerBoard, PlayerState


def test_standard_and_joker_cards_are_distinct_physical_cards():
    cards = {
        Card(rank=14, suit="s"),
        Card(rank=14, suit="h"),
        Card(joker_id=1),
        Card(joker_id=2),
    }
    assert len(cards) == 4


def test_duplicate_known_card_is_rejected():
    ace = Card(rank=14, suit="s")
    p0 = PlayerState(chair=0, board=PlayerBoard(top=(ace, None, None)))
    p1 = PlayerState(chair=1)
    with pytest.raises(ValueError, match="duplicate physical card"):
        OFCState(
            players=(p0, p1),
            hero_chair=0,
            dealer_chair=1,
            acting_chair=0,
            round_index=0,
            hero_incoming=(ace,),
            action_required=True,
        )


def test_board_capacity_is_3_5_5():
    board = PlayerBoard(
        top=(Card(14, "s"), Card(13, "s"), Card(12, "s")),
        middle=(Card(11, "s"), Card(10, "s"), Card(9, "s"), Card(8, "s"), Card(7, "s")),
        bottom=(Card(6, "s"), Card(5, "s"), Card(4, "s"), Card(3, "s"), Card(2, "s")),
    )
    assert board.filled_count() == 13
    assert board.is_complete()
