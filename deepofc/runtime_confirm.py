from __future__ import annotations

"""Fail-closed semantic verification for a *normal-play* KKPoker Confirm.

This does not click anything.  It proves that a separately attempted Confirm was
accepted by examining a fresh canonical state.  Fantasy and final-hand teardown
are intentionally excluded because their post-Confirm screen semantics differ
and require their own certified routes.
"""

from dataclasses import dataclass

from .runtime_orchestrator import validate_runtime_turn_progress
from .runtime_plan import RuntimeTurnPlan
from .state import Card, OFCState, PlayerBoard, Row


@dataclass(frozen=True)
class NormalConfirmReceipt:
    accepted: bool
    transition: str  # "same_round_handoff" | "next_round_committed"
    previous_round: int
    observed_round: int


def _board_sets(board: PlayerBoard) -> dict[Row, frozenset[Card]]:
    return {
        Row.TOP: frozenset(board.top),
        Row.MIDDLE: frozenset(board.middle),
        Row.BOTTOM: frozenset(board.bottom),
    }


def _expected_committed_board(before: OFCState, plan: RuntimeTurnPlan) -> dict[Row, frozenset[Card]]:
    hero = before.player(before.hero_chair).board
    out = {row: set(cards) for row, cards in _board_sets(hero).items()}
    by_code = {card.code: card for card in before.hero_incoming}
    for placement in plan.target_placements:
        card = by_code.get(placement.card_code)
        if card is None:
            raise ValueError("turn plan target is not present in pre-Confirm incoming set")
        out[placement.row].add(card)
    return {row: frozenset(cards) for row, cards in out.items()}


def _pending_map(state: OFCState) -> dict[str, Row]:
    return {p.card.code: p.row for p in state.hero_pending}


def validate_normal_confirm_transition(
    before: OFCState,
    after: OFCState,
    plan: RuntimeTurnPlan,
) -> NormalConfirmReceipt:
    """Prove acceptance of one normal-round Confirm from a fresh canonical state.

    Accepted evidence paths:

    1. `same_round_handoff`: KKPoker still represents the just-confirmed Hero
       cards as current-round visual placements, but Confirm is no longer Hero's
       action and ordered acting chair has moved away from Hero.

    2. `next_round_committed`: the scraper/reconstructor already advanced one
       normal round.  The prior plan's target cards must now be committed in the
       exact requested rows, and any later-round unused card must be present in
       Hero's known discard history.

    Round 4 and Fantasy are deliberately refused here; final-hand teardown and
    Fantasy UI exit need separately calibrated evidence rather than inference.
    """

    if before.hero_is_fantasy or after.hero_is_fantasy:
        raise ValueError("normal Confirm verifier does not accept Fantasy states")
    if before.round_index not in range(4):
        raise ValueError("normal Confirm verifier currently certifies rounds 0..3 only")
    if before.hero_chair != after.hero_chair or before.dealer_chair != after.dealer_chair:
        raise ValueError("Hero/dealer chair mapping changed across Confirm")
    if len(before.players) != len(after.players):
        raise ValueError("player count changed across Confirm")

    progress = validate_runtime_turn_progress(before, plan)
    if not progress.ready_for_confirm:
        raise ValueError("pre-Confirm state is not a complete Confirm-ready fixed plan")

    if after.round_index == before.round_index:
        if after.acting_chair == after.hero_chair:
            raise ValueError("same-round post-Confirm evidence still says Hero is acting")
        if after.hero_can_confirm or after.action_required:
            raise ValueError("same-round post-Confirm evidence still exposes a Hero Confirm action")
        if tuple(sorted(c.code for c in after.hero_incoming)) != plan.incoming_cards:
            raise ValueError("same-round post-Confirm incoming physical-card set changed")
        if _board_sets(after.player(after.hero_chair).board) != _board_sets(
            before.player(before.hero_chair).board
        ):
            raise ValueError("committed Hero board changed before canonical round advancement")
        expected_pending = {p.card_code: p.row for p in plan.target_placements}
        if _pending_map(after) != expected_pending:
            raise ValueError("same-round post-Confirm target placements are not preserved exactly")
        if tuple(sorted(c.code for c in after.hero_discards)) != tuple(
            sorted(c.code for c in before.hero_discards)
        ):
            raise ValueError("Hero discard history changed without a canonical round advance")
        return NormalConfirmReceipt(True, "same_round_handoff", before.round_index, after.round_index)

    if after.round_index == before.round_index + 1:
        expected_board = _expected_committed_board(before, plan)
        actual_board = _board_sets(after.player(after.hero_chair).board)
        if actual_board != expected_board:
            raise ValueError("next-round canonical board does not commit the fixed solver targets exactly")

        prior_discards = {card.code for card in before.hero_discards}
        after_discards = {card.code for card in after.hero_discards}
        expected_added = set(plan.unused_cards)
        if before.round_index == 0:
            if expected_added:
                raise ValueError("round 0 plan unexpectedly contains unused/discard cards")
            if after_discards != prior_discards:
                raise ValueError("round 0→1 transition unexpectedly changed Hero discard history")
        else:
            if after_discards != prior_discards | expected_added:
                raise ValueError("next-round discard history does not contain exactly the prior unused card")

        if len(after.hero_incoming) != 3:
            raise ValueError("advanced normal round does not expose the expected three new Hero cards")
        return NormalConfirmReceipt(True, "next_round_committed", before.round_index, after.round_index)

    raise ValueError("post-Confirm state is neither same-round handoff nor exactly one-round advancement")
