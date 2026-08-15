from deepofc.decision import evaluate_final_normal_round
from deepofc.state import Card, OFCState, PlayerBoard, PlayerState, Row


def C(code: str) -> Card:
    return Card.from_code(code)


def make_terminal_state() -> tuple[OFCState, PlayerBoard]:
    hero = PlayerBoard(
        top=(C("Qs"), C("Qh")),
        middle=(C("9c"), C("9d"), C("8c"), C("7c")),
        bottom=(C("As"), C("Ks"), C("Qc"), C("Jc"), C("Tc")),
    )
    opponent = PlayerBoard(
        top=(C("Js"), C("Jh"), C("3s")),
        middle=(C("8s"), C("8h"), C("6d"), C("5d"), C("4d")),
        bottom=(C("Ad"), C("Kd"), C("Qd"), C("Jd"), C("Td")),
    )
    # Qd is already on opponent board, so use a different third incoming card.
    incoming = (C("Qh") if False else C("Qd"), C("9h"), C("2h"))
    # Replace opponent Qd to preserve physical uniqueness in the real state.
    opponent = PlayerBoard(
        top=(C("Js"), C("Jh"), C("3s")),
        middle=(C("8s"), C("8h"), C("6d"), C("5d"), C("4d")),
        bottom=(C("Ad"), C("Kd"), C("7d"), C("Jd"), C("Td")),
    )
    state = OFCState(
        players=(
            PlayerState(chair=0, board=opponent),
            PlayerState(chair=1, board=hero),
        ),
        hero_chair=1,
        dealer_chair=1,
        acting_chair=1,
        round_index=4,
        hero_incoming=incoming,
        hero_can_prepare=True,
        hero_can_confirm=True,
        action_required=True,
    )
    return state, opponent


def test_final_round_exact_solver_chooses_only_nonfouling_escape():
    state, opponent = make_terminal_state()
    decision = evaluate_final_normal_round(state, (opponent,))
    assert len(decision.values) == 6  # bottom full: choose Top/Middle + discard
    assert decision.best_actions
    assert all(not value.foul for value in decision.best_actions)

    # The only board-valid assignment is 2h -> Top, 9h -> Middle, discard Qd.
    best = decision.best_actions[0]
    assert best.action.discard == C("Qd")
    placement = {p.card: p.row for p in best.action.placements}
    assert placement == {C("2h"): Row.TOP, C("9h"): Row.MIDDLE}


def test_fantasy_continuation_is_explicit_not_hidden_heuristic():
    state, opponent = make_terminal_state()
    base = evaluate_final_normal_round(state, (opponent,))
    boosted = evaluate_final_normal_round(
        state,
        (opponent,),
        fantasy_continuation_by_cards={14: 10.0, 15: 20.0, 16: 30.0, 17: 40.0},
    )

    by_key_base = {value.action.key(): value for value in base.values}
    by_key_boosted = {value.action.key(): value for value in boosted.values}
    assert by_key_base.keys() == by_key_boosted.keys()
    for key in by_key_base:
        before = by_key_base[key]
        after = by_key_boosted[key]
        expected = 0.0 if before.fantasy_entry_cards is None else {
            14: 10.0, 15: 20.0, 16: 30.0, 17: 40.0
        }[before.fantasy_entry_cards]
        assert after.total_value == before.current_hand_points + expected
