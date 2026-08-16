import pytest

from deepofc.actions import NormalPlacementAction, fantasy_action_board
from deepofc.baseline import choose_baseline_action, choose_baseline_decision
from deepofc.runtime_plan import build_runtime_turn_plan
from deepofc.scoring import is_foul
from deepofc.simulator import apply_normal_action
from deepofc.state import Card, OFCState, PlayerBoard, PlayerState


def C(code: str) -> Card:
    return Card.from_code(code)


def normal_round1_state(*, incoming=None) -> OFCState:
    cards = incoming or (C("Jd"), C("Ts"), C("9h"))
    return OFCState(
        players=(
            PlayerState(chair=0, board=PlayerBoard()),
            PlayerState(
                chair=1,
                board=PlayerBoard(
                    top=(C("As"),),
                    middle=(C("Kh"), C("Qh")),
                    bottom=(C("8c"), C("7c")),
                ),
            ),
        ),
        hero_chair=1,
        dealer_chair=1,
        acting_chair=1,
        round_index=1,
        hero_incoming=tuple(cards),
        hero_can_prepare=True,
        hero_can_confirm=False,
        action_required=False,
    )


def final_state(*, complete_opponent: bool, action_required: bool = False) -> OFCState:
    hero = PlayerBoard(
        top=(C("Qh"), C("Qd")),
        middle=(C("2c"), C("3c"), C("4c"), C("5c")),
        bottom=(C("9s"), C("Ts"), C("Js"), C("Qs"), C("Ks")),
    )
    opponent = (
        PlayerBoard(
            top=(C("2d"), C("2h"), C("7d")),
            middle=(C("3d"), C("3h"), C("8d"), C("8h"), C("Kd")),
            bottom=(C("4d"), C("4h"), C("9d"), C("9h"), C("Ad")),
        )
        if complete_opponent
        else PlayerBoard()
    )
    return OFCState(
        players=(PlayerState(chair=0, board=opponent), PlayerState(chair=1, board=hero)),
        hero_chair=1,
        dealer_chair=1,
        acting_chair=1,
        round_index=4,
        hero_incoming=(C("Qc"), C("6c"), C("Ac")),
        hero_can_prepare=True,
        hero_can_confirm=action_required,
        action_required=action_required,
    )


def fantasy_cards() -> tuple[Card, ...]:
    return tuple(
        C(code)
        for code in (
            "2s", "3s", "4s", "5s", "6s", "7s", "8s",
            "9s", "Ts", "Js", "Qs", "Ks", "As", "JK1",
        )
    )


def fantasy_state(cards=None) -> OFCState:
    incoming = tuple(cards or fantasy_cards())
    return OFCState(
        players=(PlayerState(chair=0), PlayerState(chair=1, fantasy=True)),
        hero_chair=1,
        dealer_chair=1,
        acting_chair=1,
        round_index=-1,
        hero_incoming=incoming,
        hero_can_prepare=True,
        hero_can_confirm=False,
        action_required=False,
    )


def test_normal_baseline_returns_legal_runtime_plan_before_confirm_is_visible():
    state = normal_round1_state()
    decision = choose_baseline_decision(state)
    assert decision.source == "normal_quality_heuristic_v1"
    assert isinstance(decision.action, NormalPlacementAction)
    assert len(decision.action.placements) == 2
    assert decision.action.discard is not None

    plan = build_runtime_turn_plan(state, decision.action)
    assert len(plan.placements_to_add) == 2
    assert len(plan.unused_cards) == 1


def test_normal_baseline_is_invariant_to_incoming_visual_order():
    cards = (C("Jd"), C("Ts"), C("9h"))
    a = choose_baseline_action(normal_round1_state(incoming=cards))
    b = choose_baseline_action(normal_round1_state(incoming=tuple(reversed(cards))))
    assert a.key() == b.key()


def test_final_normal_heuristic_avoids_obvious_foul_when_opponent_is_incomplete():
    state = final_state(complete_opponent=False)
    action = choose_baseline_action(state)
    board, _ = apply_normal_action(
        state.player(state.hero_chair).board,
        action,
        round_index=4,
        incoming=state.hero_incoming,
    )
    assert board.is_complete()
    assert not is_foul(board, equality_allowed=True)


def test_final_normal_uses_exact_kernel_when_scope_is_satisfied():
    state = final_state(complete_opponent=True, action_required=True)
    decision = choose_baseline_decision(state)
    assert decision.source == "normal_final_exact"
    board, _ = apply_normal_action(
        state.player(state.hero_chair).board,
        decision.action,
        round_index=4,
        incoming=state.hero_incoming,
    )
    assert not is_foul(board, equality_allowed=True)


def test_fantasy_baseline_builds_complete_nonfoul_board_and_runtime_plan():
    state = fantasy_state()
    decision = choose_baseline_decision(state)
    assert decision.source in {
        "fantasy_quality_beam_v1",
        "fantasy_feasibility_fallback_v1",
    }
    board = fantasy_action_board(decision.action)
    assert board.is_complete()
    assert not is_foul(board, equality_allowed=True)
    assert len(decision.action.discards) == 1

    plan = build_runtime_turn_plan(state, decision.action)
    assert plan.fantasy is True
    assert len(plan.target_placements) == 13
    assert len(plan.unused_cards) == 1


def test_fantasy_baseline_is_invariant_to_fan_reflow_order():
    cards = fantasy_cards()
    first = choose_baseline_action(fantasy_state(cards))
    second = choose_baseline_action(fantasy_state(tuple(reversed(cards))))
    assert first.key() == second.key()


def test_baseline_rejects_out_of_turn_state():
    base = normal_round1_state()
    state = OFCState(
        players=base.players,
        hero_chair=base.hero_chair,
        dealer_chair=base.dealer_chair,
        acting_chair=0,
        round_index=base.round_index,
        hero_incoming=base.hero_incoming,
        hero_can_prepare=True,
    )
    with pytest.raises(ValueError, match="acting chair"):
        choose_baseline_action(state)
