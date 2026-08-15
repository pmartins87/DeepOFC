from math import comb

from deepofc.fantasy_solver import (
    _resolve_cached_candidates,
    _resolve_opponent,
    _score_valid_hero_ranks,
    evaluate_fantasy_exact_subsets,
)
from deepofc.scoring import (
    _canonical_eval_key,
    _five_rank_candidates_cached,
    _top_rank_candidates_cached,
    completed_board_ranks,
    is_foul,
    pairwise_points_standard,
)
from deepofc.simulator import settle_raw_points
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


def test_subset_rank_resolver_exactly_matches_board_aware_joker_evaluator():
    board = PlayerBoard(
        top=(C("As"), C("Ah"), C("JK1")),
        middle=(C("Ks"), C("Kh"), C("Qd"), C("Qc"), C("2s")),
        bottom=(C("5s"), C("6d"), C("7c"), C("8h"), C("9s")),
    )
    top_candidates = _top_rank_candidates_cached(_canonical_eval_key(board.top, 3))
    middle_candidates = _five_rank_candidates_cached(_canonical_eval_key(board.middle, 5))
    bottom_candidates = _five_rank_candidates_cached(_canonical_eval_key(board.bottom, 5))
    resolved = _resolve_cached_candidates(
        top_candidates,
        middle_candidates,
        bottom_candidates,
        equality_allowed=True,
    )
    assert resolved == completed_board_ranks(board)
    assert resolved is not None
    # Row-local AA+Joker would be trips, but board-aware resolution keeps AA pair.
    assert resolved[0].category.name == "PAIR"


def test_resolved_fast_pairwise_score_matches_canonical_scoring_with_joker():
    hero = PlayerBoard(
        top=(C("As"), C("Ah"), C("JK1")),
        middle=(C("Ks"), C("Kh"), C("Qd"), C("Qc"), C("2s")),
        bottom=(C("5s"), C("6d"), C("7c"), C("8h"), C("9s")),
    )
    villain = opponent_board()
    hero_ranks = completed_board_ranks(hero)
    fast = _score_valid_hero_ranks(
        hero_ranks,
        (_resolve_opponent(villain, equality_allowed=True),),
    )
    canonical = pairwise_points_standard(hero, villain).total_points
    assert fast == canonical


def test_exact_fantasy14_subset_solver_returns_canonical_global_optimum_candidate():
    state = fantasy14_state()
    decision = evaluate_fantasy_exact_subsets(state)

    assert decision.stats.incoming_cards == 14
    assert decision.stats.top_subsets == comb(14, 3) == 364
    assert decision.stats.five_subsets == comb(14, 5) == 2002
    assert decision.stats.valid_boards_scored > 0
    assert decision.tied_best_count >= 1

    incoming = set(state.hero_incoming)
    assert decision.action.placed_cards | set(decision.action.discards) == incoming
    assert len(decision.action.discards) == 1
    assert decision.board.is_complete()
    assert not is_foul(decision.board, equality_allowed=True)
    assert decision.resolved_ranks == completed_board_ranks(decision.board)

    canonical = settle_raw_points((decision.board, opponent_board())).points_by_chair[0]
    assert decision.current_hand_points == canonical
    assert decision.total_value == float(canonical)


def test_refantasy_continuation_is_explicit_in_fantasy_kernel():
    state = fantasy14_state()
    base = evaluate_fantasy_exact_subsets(state)
    boosted = evaluate_fantasy_exact_subsets(
        state,
        refantasy_continuation_value=1000.0,
    )
    assert boosted.total_value == boosted.current_hand_points + (
        1000.0 if boosted.refantasy_qualifies else 0.0
    )
    # A sufficiently large continuation cannot make the optimum worse.
    assert boosted.total_value >= base.total_value
