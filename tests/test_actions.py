from deepofc.actions import enumerate_normal_actions
from deepofc.state import Card, OFCState, PlayerBoard, PlayerState


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
