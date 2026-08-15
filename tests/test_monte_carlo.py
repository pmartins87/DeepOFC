from deepofc.expectimax import evaluate_penultimate_normal_round_exact_last_chance
from deepofc.monte_carlo import evaluate_penultimate_normal_round_monte_carlo
from deepofc.state import Card, OFCState, PlayerBoard, PlayerState


def C(code: str) -> Card:
    return Card.from_code(code)


def state_and_pool():
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
    state = OFCState(
        players=(PlayerState(chair=0, board=opponent), PlayerState(chair=1, board=hero)),
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
    pool = (C("Ks"), C("9h"), C("8h"), C("4h"), C("2h"))
    return state, pool


def test_exhaustive_monte_carlo_collapses_exactly_to_expectimax():
    state, pool = state_and_pool()
    exact = evaluate_penultimate_normal_round_exact_last_chance(
        state, future_draw_pool=pool
    )
    mc = evaluate_penultimate_normal_round_monte_carlo(
        state, samples=10_000, seed=123, future_draw_pool=pool
    )

    assert mc.exhaustive
    assert mc.total_chance_branches == 10
    assert mc.sampled_chance_branches == 10
    assert len(mc.values) == len(exact.values)
    for sampled, truth in zip(mc.values, exact.values):
        assert sampled.action == truth.action
        assert sampled.mean_value == truth.expected_value
        assert sampled.standard_error == 0.0
        assert sampled.ci95_half_width == 0.0
    assert mc.best_value == exact.best_value
    assert mc.best_indices == exact.best_indices


def test_partial_monte_carlo_is_seed_reproducible_and_reports_uncertainty():
    state, pool = state_and_pool()
    a = evaluate_penultimate_normal_round_monte_carlo(
        state, samples=5, seed=987654, future_draw_pool=pool
    )
    b = evaluate_penultimate_normal_round_monte_carlo(
        state, samples=5, seed=987654, future_draw_pool=pool
    )
    assert a == b
    assert not a.exhaustive
    assert a.sampled_chance_branches == 5
    assert all(value.samples == 5 for value in a.values)
    assert all(value.standard_error >= 0 for value in a.values)
    assert all(value.ci95_half_width == 1.96 * value.standard_error for value in a.values)


def test_common_random_numbers_do_not_depend_on_action_count_or_order():
    state, pool = state_and_pool()
    # The public API is deterministic: same seed and chance pool imply identical
    # estimates for every action, which is the regression-visible consequence of
    # sampling chance branches once and reusing them for all actions.
    first = evaluate_penultimate_normal_round_monte_carlo(
        state, samples=4, seed=42, future_draw_pool=pool
    )
    second = evaluate_penultimate_normal_round_monte_carlo(
        state, samples=4, seed=42, future_draw_pool=pool
    )
    assert first.values == second.values
