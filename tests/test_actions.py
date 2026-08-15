from itertools import islice

import pytest

from deepofc.actions import (
    FantasyPlacementAction,
    count_fantasy_actions,
    enumerate_normal_actions,
    fantasy_action_board,
    fantasy_action_is_foul,
    iter_fantasy_actions,
)
from deepofc.state import Card, OFCState, PendingPlacement, PlayerBoard, PlayerState, Row


def C(code: str) -> Card:
    return Card.from_code(code)


def make_state(*, round_index: int, board: PlayerBoard, incoming: tuple[Card, ...]) -> OFCState:
    return OFCState(
        players=(PlayerState(chair=0), PlayerState(chair=1, board=board)),
        hero_chair=1,
        dealer_chair=1,
        acting_chair=1,
        round_index=round_index,
        hero_incoming=incoming,
        hero_can_prepare=True,
        hero_can_confirm=True,
        action_required=True,
    )


def fantasy_cards(count: int) -> tuple[Card, ...]:
    pool = tuple(
        C(code)
        for code in (
            "2s", "3s", "4s", "5s", "6s", "7s", "8s", "9s", "Ts",
            "Js", "Qs", "Ks", "As", "Ah", "Kh", "Qh", "JK1",
        )
    )
    return pool[:count]


def make_fantasy_state(count: int) -> OFCState:
    return OFCState(
        players=(PlayerState(chair=0), PlayerState(chair=1, fantasy=True)),
        hero_chair=1,
        dealer_chair=1,
        acting_chair=1,
        round_index=-1,
        hero_incoming=fantasy_cards(count),
        hero_can_prepare=True,
        hero_can_confirm=True,
        action_required=True,
    )


def fantasy_action(
    *,
    top: tuple[str, str, str],
    middle: tuple[str, str, str, str, str],
    bottom: tuple[str, str, str, str, str],
    discards: tuple[str, ...] = ("2d",),
) -> FantasyPlacementAction:
    placements = (
        *(PendingPlacement(card=C(code), row=Row.TOP) for code in top),
        *(PendingPlacement(card=C(code), row=Row.MIDDLE) for code in middle),
        *(PendingPlacement(card=C(code), row=Row.BOTTOM) for code in bottom),
    )
    return FantasyPlacementAction(
        placements=placements,
        discards=tuple(C(code) for code in discards),
    )


def test_round_zero_empty_board_has_232_distinct_row_assignments():
    state = make_state(
        round_index=0,
        board=PlayerBoard(),
        incoming=(C("As"), C("Kh"), C("Qc"), C("Jd"), C("Ts")),
    )
    actions = enumerate_normal_actions(state)
    # 3^5 assignments minus assignments putting 4 or 5 cards on 3-slot Top:
    # 243 - (C(5,4)*2 + C(5,5)) = 232.
    assert len(actions) == 232
    assert all(a.discard is None for a in actions)
    assert all(len(a.placements) == 5 for a in actions)


def test_later_round_empty_capacity_has_27_actions():
    state = make_state(
        round_index=1,
        board=PlayerBoard(top=(C("As"),), middle=(C("Kh"),), bottom=(C("Qc"),)),
        incoming=(C("Jd"), C("Ts"), C("9h")),
    )
    actions = enumerate_normal_actions(state)
    assert len(actions) == 27  # 3 discard choices x 3^2 row choices
    assert {a.discard for a in actions} == set(state.hero_incoming)
    assert all(len(a.placements) == 2 for a in actions)


def test_row_capacity_prunes_only_illegal_assignments():
    state = make_state(
        round_index=4,
        board=PlayerBoard(
            top=(C("As"), C("Kh")),       # one free
            middle=(C("Qc"), C("Jd"), C("Ts")),  # two free
            bottom=(C("9h"), C("8h"), C("7h"), C("6h"), C("5h")),  # full
        ),
        incoming=(C("4c"), C("3d"), C("2s")),
    )
    actions = enumerate_normal_actions(state)
    # For each discard, remaining two cards can be Top/Middle, Middle/Top or
    # Middle/Middle. Top/Top overflows and Bottom is unavailable.
    assert len(actions) == 9
    for action in actions:
        rows = [p.row.value for p in action.placements]
        assert "bottom" not in rows
        assert rows.count("top") <= 1


def test_actions_cover_each_incoming_card_exactly_once_as_place_or_discard():
    state = make_state(
        round_index=2,
        board=PlayerBoard(top=(C("As"),), middle=(C("Kh"),), bottom=(C("Qc"),)),
        incoming=(C("Jd"), C("Ts"), C("9h")),
    )
    incoming = set(state.hero_incoming)
    for action in enumerate_normal_actions(state):
        assert action.discard is not None
        assert action.placed_cards | {action.discard} == incoming
        assert not (action.placed_cards & {action.discard})


def test_fantasy_action_space_counts_are_exact_but_not_materialized():
    assert count_fantasy_actions(make_fantasy_state(14)) == 1_009_008
    assert count_fantasy_actions(make_fantasy_state(15)) == 7_567_560
    assert count_fantasy_actions(make_fantasy_state(16)) == 40_360_320
    assert count_fantasy_actions(make_fantasy_state(17)) == 171_531_360


def test_first_fantasy_actions_fill_3_5_5_and_partition_every_physical_card():
    state = make_fantasy_state(14)
    incoming = set(state.hero_incoming)
    for action in islice(iter_fantasy_actions(state), 20):
        assert len(action.placements) == 13
        assert len(action.discards) == 1
        assert action.placed_cards | set(action.discards) == incoming
        assert not (action.placed_cards & set(action.discards))
        rows = [placement.row for placement in action.placements]
        assert rows.count(Row.TOP) == 3
        assert rows.count(Row.MIDDLE) == 5
        assert rows.count(Row.BOTTOM) == 5


def test_fantasy_iterator_supports_17_cards_without_allocating_171m_actions():
    state = make_fantasy_state(17)
    first = next(iter_fantasy_actions(state))
    assert len(first.discards) == 4
    assert len(first.placements) == 13


def test_normal_generator_rejects_fantasy_state():
    with pytest.raises(ValueError, match="Fantasy"):
        enumerate_normal_actions(make_fantasy_state(14))


def test_fantasy_action_materializes_canonical_board_without_visual_slot_semantics():
    action = fantasy_action(
        top=("As", "Ah", "JK1"),
        middle=("Ks", "Kh", "Qd", "Qc", "2s"),
        bottom=("5s", "6d", "7c", "8h", "9s"),
    )
    board = fantasy_action_board(action)
    assert set(board.top) == {C("As"), C("Ah"), C("JK1")}
    assert set(board.middle) == {C("Ks"), C("Kh"), C("Qd"), C("Qc"), C("2s")}
    assert set(board.bottom) == {C("5s"), C("6d"), C("7c"), C("8h"), C("9s")}


def test_fantasy_action_joker_uses_board_aware_nonfoul_assignment():
    # Top AA+JK is locally AAA, but Middle is only two pair. The board-aware
    # Joker evaluator must downgrade Top to AAK rather than mark this action as
    # foul merely because the locally strongest Joker use would break the board.
    action = fantasy_action(
        top=("As", "Ah", "JK1"),
        middle=("Ks", "Kh", "Qd", "Qc", "2s"),
        bottom=("5s", "6d", "7c", "8h", "9s"),
    )
    assert fantasy_action_is_foul(action) is False


def test_fantasy_action_reports_true_foul_when_no_joker_assignment_can_rescue_board():
    # Even the weakest useful Joker substitution cannot make Top AA <= a mere
    # Middle KK pair, so this is a genuine placement foul rather than an
    # avoidable wildcard-choice foul.
    action = fantasy_action(
        top=("As", "Ah", "JK1"),
        middle=("Ks", "Kh", "Qd", "Jc", "9s"),
        bottom=("5d", "6d", "7d", "8d", "9d"),
    )
    assert fantasy_action_is_foul(action) is True
