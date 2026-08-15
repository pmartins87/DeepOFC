import pytest

from deepofc.scoring import (
    HandCategory,
    HandRank,
    is_foul,
    rank_five,
    rank_top,
    royalty,
)
from deepofc.state import Card, PlayerBoard, Row


def c(rank: int, suit: str) -> Card:
    return Card(rank=rank, suit=suit)


def test_top_rank_pair_and_trips():
    assert rank_top([c(12, "s"), c(12, "h"), c(14, "d")]) == HandRank(
        HandCategory.PAIR, (12, 14)
    )
    assert rank_top([c(7, "s"), c(7, "h"), c(7, "d")]) == HandRank(
        HandCategory.TRIPS, (7,)
    )


def test_five_card_wheel_is_five_high_straight():
    rank = rank_five([c(14, "s"), c(2, "h"), c(3, "d"), c(4, "c"), c(5, "s")])
    assert rank == HandRank(HandCategory.STRAIGHT, (5,))


def test_royalty_tables_match_supplied_kkpoker_frames():
    assert royalty(Row.TOP, HandRank(HandCategory.PAIR, (6, 14))) == 1
    assert royalty(Row.TOP, HandRank(HandCategory.PAIR, (14, 13))) == 9
    assert royalty(Row.TOP, HandRank(HandCategory.TRIPS, (2,))) == 10
    assert royalty(Row.TOP, HandRank(HandCategory.TRIPS, (14,))) == 22

    assert royalty(Row.MIDDLE, HandRank(HandCategory.TRIPS, (9, 14, 2))) == 2
    assert royalty(Row.MIDDLE, HandRank(HandCategory.STRAIGHT, (10,))) == 4
    assert royalty(Row.MIDDLE, HandRank(HandCategory.FLUSH, (14, 10, 8, 5, 2))) == 8
    assert royalty(Row.MIDDLE, HandRank(HandCategory.FULL_HOUSE, (10, 8))) == 12
    assert royalty(Row.MIDDLE, HandRank(HandCategory.QUADS, (10, 8))) == 20
    assert royalty(Row.MIDDLE, HandRank(HandCategory.STRAIGHT_FLUSH, (9,))) == 30
    assert royalty(Row.MIDDLE, HandRank(HandCategory.STRAIGHT_FLUSH, (14,))) == 50

    assert royalty(Row.BOTTOM, HandRank(HandCategory.STRAIGHT, (10,))) == 2
    assert royalty(Row.BOTTOM, HandRank(HandCategory.FLUSH, (14, 10, 8, 5, 2))) == 4
    assert royalty(Row.BOTTOM, HandRank(HandCategory.FULL_HOUSE, (10, 8))) == 6
    assert royalty(Row.BOTTOM, HandRank(HandCategory.QUADS, (10, 8))) == 10
    assert royalty(Row.BOTTOM, HandRank(HandCategory.STRAIGHT_FLUSH, (9,))) == 15
    assert royalty(Row.BOTTOM, HandRank(HandCategory.STRAIGHT_FLUSH, (14,))) == 25


def test_joker_evaluation_fails_closed_until_r1():
    with pytest.raises(NotImplementedError, match="R1"):
        rank_top([Card(joker_id=1), c(12, "s"), c(12, "h")])


def test_equal_middle_and_bottom_is_legal_only_under_current_client_equality_rule():
    # Bottom and middle are exactly equal poker ranks (AAKQJ) using distinct
    # physical suits. Top is weaker. The supplied current-client rule says
    # Bottom >= Middle >= Top, so this board is valid under the target rule but
    # would foul under a strict-outrank policy.
    board = PlayerBoard(
        top=(c(13, "s"), c(12, "h"), c(9, "d")),
        middle=(c(14, "s"), c(14, "h"), c(13, "d"), c(12, "c"), c(11, "h")),
        bottom=(c(14, "d"), c(14, "c"), c(13, "h"), c(12, "s"), c(11, "d")),
    )
    assert is_foul(board, equality_allowed=True) is False
    assert is_foul(board, equality_allowed=False) is True
