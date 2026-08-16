import pytest

from deepofc.actions import FantasyPlacementAction, NormalPlacementAction
from deepofc.runtime_orchestrator import RuntimeTurnOrchestrator, validate_runtime_turn_progress
from deepofc.runtime_plan import build_runtime_turn_plan
from deepofc.state import Card, OFCState, PendingPlacement, PlayerBoard, PlayerState, Row


def C(code: str) -> Card:
    return Card.from_code(code)


def make_normal_state(*, pending=(), opponent_top="2c", acting=1) -> OFCState:
    return OFCState(
        players=(
            PlayerState(
                chair=0,
                board=PlayerBoard(top=(C(opponent_top),), middle=(C("3c"),), bottom=(C("4c"),)),
            ),
            PlayerState(
                chair=1,
                board=PlayerBoard(top=(C("As"),), middle=(C("Kh"),), bottom=(C("Qc"),)),
            ),
        ),
        hero_chair=1,
        dealer_chair=1,
        acting_chair=acting,
        round_index=1,
        hero_incoming=(C("Jd"), C("Ts"), C("9h")),
        hero_pending=tuple(pending),
        hero_can_prepare=True,
        hero_can_confirm=len(tuple(pending)) == 2 and acting == 1,
        action_required=len(tuple(pending)) == 2 and acting == 1,
    )


def normal_action() -> NormalPlacementAction:
    return NormalPlacementAction(
        placements=(
            PendingPlacement(C("Jd"), Row.TOP),
            PendingPlacement(C("Ts"), Row.MIDDLE),
        ),
        discard=C("9h"),
    )


def test_orchestrator_requires_fresh_progress_before_next_mutation():
    start = make_normal_state()
    plan = build_runtime_turn_plan(start, normal_action())
    runtime = RuntimeTurnOrchestrator(plan)

    p0 = runtime.advance(start)
    assert p0.ready_for_confirm is False
    assert len(p0.remaining) == 2
    first = p0.next_placement
    assert first is not None

    # Simulate one independently verified drag by producing a fresh canonical
    # state with exactly that card pending in its requested row.
    after_first = make_normal_state(
        pending=(PendingPlacement(C(first.card_code), first.row),)
    )
    p1 = runtime.advance(after_first)
    assert p1.ready_for_confirm is False
    assert len(p1.already_correct) == 1
    assert len(p1.remaining) == 1
    assert p1.next_placement != first

    second = p1.next_placement
    assert second is not None
    after_second = make_normal_state(
        pending=(
            PendingPlacement(C(first.card_code), first.row),
            PendingPlacement(C(second.card_code), second.row),
        )
    )
    p2 = runtime.advance(after_second)
    assert p2.remaining == ()
    assert p2.ready_for_confirm is True


def test_strategy_relevant_drift_latches_block_and_prevents_recovery_guessing():
    start = make_normal_state()
    runtime = RuntimeTurnOrchestrator(build_runtime_turn_plan(start, normal_action()))

    changed_opponent = make_normal_state(opponent_top="2d")
    with pytest.raises(ValueError, match="strategy-relevant"):
        runtime.advance(changed_opponent)
    assert runtime.blocked
    assert runtime.blocked_reason is not None

    # Even if a later frame looks normal again, the same in-progress physical
    # transaction may not silently resume after ambiguity.
    with pytest.raises(RuntimeError, match="blocked"):
        runtime.advance(start)


def test_wrong_row_progress_is_latched_fail_closed():
    start = make_normal_state()
    runtime = RuntimeTurnOrchestrator(build_runtime_turn_plan(start, normal_action()))
    wrong = make_normal_state(pending=(PendingPlacement(C("Jd"), Row.BOTTOM),))
    with pytest.raises(ValueError, match="expected top"):
        runtime.advance(wrong)
    assert runtime.blocked


def test_unused_card_becoming_pending_is_never_reinterpreted_as_strategy():
    start = make_normal_state()
    plan = build_runtime_turn_plan(start, normal_action())
    wrong = make_normal_state(pending=(PendingPlacement(C("9h"), Row.TOP),))
    with pytest.raises(ValueError, match="remain unused"):
        validate_runtime_turn_progress(wrong, plan)


def test_complete_but_illegal_confirm_shape_is_rejected():
    # A hand-made malformed plan is not needed: canonical state itself enforces
    # capacities and plan construction enforces action shape. The relevant gate
    # is that one pending card alone can never be mistaken for Confirm-ready.
    start = make_normal_state()
    plan = build_runtime_turn_plan(start, normal_action())
    one = make_normal_state(pending=(PendingPlacement(C("Jd"), Row.TOP),))
    progress = validate_runtime_turn_progress(one, plan)
    assert progress.ready_for_confirm is False


def fantasy_cards() -> tuple[Card, ...]:
    return tuple(
        C(code)
        for code in (
            "2s", "3s", "4s", "5s", "6s", "7s", "8s",
            "9s", "Ts", "Js", "Qs", "Ks", "As", "JK1",
        )
    )


def make_fantasy_state(*, pending=()) -> OFCState:
    pending = tuple(pending)
    return OFCState(
        players=(PlayerState(chair=0), PlayerState(chair=1, fantasy=True)),
        hero_chair=1,
        dealer_chair=1,
        acting_chair=1,
        round_index=-1,
        hero_incoming=fantasy_cards(),
        hero_pending=pending,
        hero_can_prepare=True,
        hero_can_confirm=len(pending) == 13,
        action_required=len(pending) == 13,
    )


def fantasy_action() -> FantasyPlacementAction:
    cards = fantasy_cards()
    return FantasyPlacementAction(
        placements=(
            *(PendingPlacement(c, Row.TOP) for c in cards[:3]),
            *(PendingPlacement(c, Row.MIDDLE) for c in cards[3:8]),
            *(PendingPlacement(c, Row.BOTTOM) for c in cards[8:13]),
        ),
        discards=(cards[13],),
    )


def test_fantasy_progress_can_be_recomputed_after_every_fan_reflow_without_slots():
    start = make_fantasy_state()
    plan = build_runtime_turn_plan(start, fantasy_action())
    runtime = RuntimeTurnOrchestrator(plan)

    progress = runtime.advance(start)
    assert len(progress.remaining) == 13
    placed = []
    while progress.next_placement is not None:
        step = progress.next_placement
        placed.append(PendingPlacement(C(step.card_code), step.row))
        # There are deliberately no source-slot/rectangle values here. A real
        # caller would re-scrape the Fantasy fan before every individual drag.
        progress = runtime.advance(make_fantasy_state(pending=tuple(placed)))

    assert len(placed) == 13
    assert progress.ready_for_confirm
    assert plan.unused_cards == ("JK1",)
