import pytest

from deepofc.scoring import (
    HandCategory,
    HandRank,
    is_foul,
    pairwise_points_standard,
    rank_five,
    rank_top,
    royalty,
)
from deepofc.state import Card, PlayerBoard, Row


def c(rank: int, suit: str) -> Card:
    return Card(rank=rank, suit=suit)


def C(code: str) -> Card:
    return Card.from_code(code)


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


def _hero_scoop_board() -> PlayerBoard:
    # QQ top (7 royalty), 7-high straight middle (4), A-high flush bottom (4).
    return PlayerBoard(
        top=(C("Qs"), C("Qh"), C("2c")),
        middle=(C("3s"), C("4d"), C("5c"), C("6c"), C("7d")),
        bottom=(C("Ah"), C("Kh"), C("9h"), C("6h"), C("3h")),
    )


def _opponent_valid_board() -> PlayerBoard:
    # JJ top (6 royalty), TT88 two-pair middle (0), 8-high straight bottom (2).
    return PlayerBoard(
        top=(C("Js"), C("Jd"), C("2h")),
        middle=(C("Tc"), C("Th"), C("8d"), C("8c"), C("4s")),
        bottom=(C("4c"), C("5h"), C("6d"), C("7c"), C("8s")),
    )


def _fouled_board() -> PlayerBoard:
    # AA top outranks KK middle, so this is fouled even though bottom is strong.
    return PlayerBoard(
        top=(C("As"), C("Ah"), C("2c")),
        middle=(C("Ks"), C("Kh"), C("Qd"), C("Jc"), C("9s")),
        bottom=(C("5d"), C("6d"), C("7d"), C("8d"), C("9d")),
    )


def test_pairwise_raw_points_include_rows_scoop_and_royalty_difference():
    score = pairwise_points_standard(_hero_scoop_board(), _opponent_valid_board())
    assert not score.hero_foul
    assert not score.opponent_foul
    assert (score.top_points, score.middle_points, score.bottom_points) == (1, 1, 1)
    assert score.row_points == 3
    assert score.scoop_bonus == 3
    assert score.hero_royalties == 15
    assert score.opponent_royalties == 8
    assert score.royalty_difference == 7
    assert score.total_points == 13


def test_exactly_one_fouled_player_is_automatic_scoop_and_loses_royalties():
    score = pairwise_points_standard(_fouled_board(), _opponent_valid_board())
    assert score.hero_foul
    assert not score.opponent_foul
    assert (score.top_points, score.middle_points, score.bottom_points) == (-1, -1, -1)
    assert score.scoop_bonus == -3
    assert score.hero_royalties == 0
    assert score.opponent_royalties == 8
    assert score.total_points == -14

    inverse = pairwise_points_standard(_opponent_valid_board(), _fouled_board())
    assert inverse.total_points == 14
    assert inverse.hero_royalties == 8
    assert inverse.opponent_royalties == 0


def test_both_players_fouling_fails_closed_until_source_rule_is_frozen():
    with pytest.raises(NotImplementedError, match="both-player foul"):
        pairwise_points_standard(_fouled_board(), _fouled_board())
