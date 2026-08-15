from deepofc.fantasy_solver import evaluate_fantasy_exact_subsets
from deepofc.fantasy_solver_v2 import evaluate_fantasy_exact_subsets_v2
from deepofc.state import Card, OFCState, PlayerBoard, PlayerState


def C(code: str) -> Card:
    return Card.from_code(code)


def opponent_board() -> PlayerBoard:
    return PlayerBoard(
        top=(C("6c"), C("6d"), C("3c")),
        middle=(C("5c"), C("5d"), C("4c"), C("4d"), C("2c")),
        bottom=(C("9c"), C("Tc"), C("Jc"), C("Qc"), C("Kc")),
    )


def fantasy14_state() -> OFCState:
    incoming = tuple(
        C(code)
        for code in (
            "As", "Ah", "Ks", "Kh", "Qs", "Qh", "Js", "Jh",
            "Ts", "Th", "9s", "8s", "7s", "2s",
        )
    )
    return OFCState(
        players=(
            PlayerState(chair=0, board=opponent_board()),
            PlayerState(chair=1, fantasy=True),
        ),
        hero_chair=1,
        dealer_chair=1,
        acting_chair=1,
        round_index=-1,
        hero_incoming=incoming,
        hero_can_prepare=True,
        hero_can_confirm=True,
        action_required=True,
    )


def test_v2_exact_value_matches_certified_v1_on_fantasy14():
    state = fantasy14_state()
    v1 = evaluate_fantasy_exact_subsets(state)
    v2 = evaluate_fantasy_exact_subsets_v2(state).decision
    assert v2.current_hand_points == v1.current_hand_points == 60
    assert v2.total_value == v1.total_value
    assert v2.resolved_ranks == v1.resolved_ranks


def test_v2_exact_value_matches_v1_with_positive_refantasy_value():
    state = fantasy14_state()
    v1 = evaluate_fantasy_exact_subsets(state, refantasy_continuation_value=37.0)
    v2 = evaluate_fantasy_exact_subsets_v2(
        state, refantasy_continuation_value=37.0
    ).decision
    assert v2.total_value == v1.total_value
    assert v2.current_hand_points == v1.current_hand_points
    assert v2.refantasy_qualifies == v1.refantasy_qualifies


def test_v2_rejects_negative_continuation_instead_of_using_invalid_monotonicity():
    state = fantasy14_state()
    try:
        evaluate_fantasy_exact_subsets_v2(
            state, refantasy_continuation_value=-1.0
        )
    except ValueError as exc:
        assert "non-negative" in str(exc)
    else:
        raise AssertionError("V2 must fail closed on negative continuation")
