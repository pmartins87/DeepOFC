from __future__ import annotations

import pytest

from deepofc.scoring import is_foul, pairwise_points_standard
from deepofc.state import Card, PlayerBoard
from m5r_full_game_remainder_envelope import (
    GLOBAL_RAW_POINT_ABS_BOUND,
    MAX_BOARD_ROYALTY,
    UndefinedBothFoulSettlement,
    p0_raw_point_interval,
    raw_point_remainder_envelope,
)


def _cards(*codes: str):
    return tuple(Card.from_code(code) for code in codes)


def _valid_pair() -> tuple[PlayerBoard, PlayerBoard]:
    hero = PlayerBoard(
        top=_cards("2c", "3d", "7h"),
        middle=_cards("5c", "5d", "8h", "9s", "Jc"),
        bottom=_cards("Kc", "Kd", "4h", "8s", "Tc"),
    )
    opponent = PlayerBoard(
        top=_cards("2d", "4c", "6s"),
        middle=_cards("6c", "6d", "8d", "9h", "Qs"),
        bottom=_cards("Qc", "Qd", "3h", "7s", "Ts"),
    )
    return hero, opponent


def _foul_board() -> PlayerBoard:
    return PlayerBoard(
        top=_cards("Ac", "Ad", "Ah"),
        middle=_cards("2c", "2d", "7c", "9d", "Jh"),
        bottom=_cards("Ks", "Kh", "3c", "6d", "8h"),
    )


def test_scoring_derived_global_bound_is_103_raw_points() -> None:
    assert MAX_BOARD_ROYALTY == 97
    assert GLOBAL_RAW_POINT_ABS_BOUND == 103


def test_empty_partial_boards_receive_global_safe_envelope() -> None:
    envelope = raw_point_remainder_envelope(PlayerBoard(), PlayerBoard())
    assert envelope.lower_raw_points == -103
    assert envelope.upper_raw_points == 103
    assert envelope.width == 206
    assert envelope.exact_terminal is False


def test_complete_terminal_collapses_to_exact_scoring_value() -> None:
    hero, opponent = _valid_pair()
    exact = pairwise_points_standard(hero, opponent).total_points
    envelope = raw_point_remainder_envelope(hero, opponent)
    assert envelope.exact_terminal is True
    assert envelope.lower_raw_points == exact
    assert envelope.upper_raw_points == exact
    assert envelope.contains(exact)


def test_one_complete_board_tightens_global_envelope() -> None:
    hero, opponent = _valid_pair()
    partial_opponent = PlayerBoard(
        top=opponent.top,
        middle=opponent.middle,
        bottom=opponent.bottom[:-1],
    )
    envelope = raw_point_remainder_envelope(hero, partial_opponent)
    assert envelope.width < 206
    assert -103 <= envelope.lower_raw_points <= envelope.upper_raw_points <= 103


def test_p0_callback_matches_primary_envelope() -> None:
    hero, opponent = _valid_pair()
    partial = PlayerBoard(
        top=opponent.top,
        middle=opponent.middle,
        bottom=opponent.bottom[:-1],
    )
    envelope = raw_point_remainder_envelope(hero, partial)
    assert p0_raw_point_interval(hero, partial) == (
        float(envelope.lower_raw_points),
        float(envelope.upper_raw_points),
    )


def test_complete_both_foul_fails_closed_instead_of_inventing_utility() -> None:
    hero = _foul_board()
    opponent = PlayerBoard(
        top=_cards("Qs", "Qh", "Qd"),
        middle=_cards("4c", "4d", "8c", "Ts", "Jd"),
        bottom=_cards("Kc", "Kd", "5h", "9c", "Tc"),
    )
    assert is_foul(hero, equality_allowed=True)
    assert is_foul(opponent, equality_allowed=True)
    with pytest.raises(UndefinedBothFoulSettlement):
        raw_point_remainder_envelope(hero, opponent)
