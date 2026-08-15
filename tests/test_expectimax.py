from deepofc.expectimax import evaluate_penultimate_normal_round_exact_last_chance
from deepofc.state import Card, OFCState, PlayerBoard, PlayerState


def C(code: str) -> Card:
    return Card.from_code(code)


def penultimate_state() -> OFCState:
    hero = PlayerBoard(
        top=(C("6s"), C("6h")),
        middle=(C("7s"), C("7h"), C("5s")),
        bottom=(C("9s"), C("Ts"), C("Js"), C("Qs")),
    )
    opponent = PlayerBoard(
        top=(C("5c"), C("5d"), C("2c")),
        middle=(C("8c"), C("8d"), C("7c"), C("6c"), C("4c")),
        bottom=(C("Ac"), C("Kc"), C("Qc"), C("Jc"), C("Tc")),
    )
    return OFCState(
        players=(
            PlayerState(chair=0, board=opponent),
            PlayerState(chair=1, board=hero),
        ),
        hero_chair=1,
        dealer_chair=0,
        acting_chair=1,
        round_index=3,
        hero_incoming=(C("Ah"), C("8s"), C("4s")),
        hero_discards=(C("2s"), C("3s")),
        hero_can_prepare=True,
        hero_can_confirm=True,
        action_required=True,
    )


def test_penultimate_exact_reduced_chance_subgame_is_deterministic():
    state = penultimate_state()
    pool = (C("Ks"), C("9h"), C("8h"), C("4h"), C("2h"))
    first = evaluate_penultimate_normal_round_exact_last_chance(
        state,
        future_draw_pool=pool,
    )
    second = evaluate_penultimate_normal_round_exact_last_chance(
        state,
        future_draw_pool=pool,
    )

    assert first == second
    assert first.chance_pool_size == 5
    assert first.chance_branches_per_action == 10
    assert first.best_actions
    assert all(value.chance_branches == 10 for value in first.values)
    assert all(value.min_branch_value <= value.expected_value <= value.max_branch_value for value in first.values)


def test_penultimate_exact_continuation_values_are_explicit_and_monotone():
    state = penultimate_state()
    pool = (C("Ks"), C("9h"), C("8h"), C("4h"), C("2h"))
    base = evaluate_penultimate_normal_round_exact_last_chance(
        state,
        future_draw_pool=pool,
    )
    boosted = evaluate_penultimate_normal_round_exact_last_chance(
        state,
        future_draw_pool=pool,
        fantasy_continuation_by_cards={14: 10.0, 15: 20.0, 16: 30.0, 17: 40.0},
    )
    assert boosted.best_value >= base.best_value


def test_penultimate_rejects_physically_unavailable_card_in_restricted_pool():
    state = penultimate_state()
    try:
        evaluate_penultimate_normal_round_exact_last_chance(
            state,
            future_draw_pool=(C("Ks"), C("9h"), C("Ah")),
        )
    except ValueError as exc:
        assert "not physically drawable" in str(exc)
    else:
        raise AssertionError("used current incoming card must not re-enter chance deck")
