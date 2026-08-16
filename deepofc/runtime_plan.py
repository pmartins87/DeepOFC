from __future__ import annotations

"""Versioned bridge from a DeepOFC strategy action to an OH UI turn plan.

This module deliberately contains **no strategy**.  It accepts an action already
chosen by a solver/policy and translates only its canonical physical-card row
membership into a fail-closed execution contract for the OpenHoldem R10 layer.

Important KKPoker facts reflected here:

- strategic state is row membership, not left-to-right visual slot identity;
- tentative Hero placements may already exist before Confirm;
- an already-correct tentative placement should be preserved, not dragged again;
- a tentative card in a row that disagrees with the solver action currently
  requires rearrangement support and therefore fails closed;
- unused/discard cards are intentionally left loose; no invented discard gesture
  is part of the plan;
- Fantasy fan geometry may reflow after every drag, so this plan never stores UI
  rectangles.  R10 must resolve each card's fresh source rectangle immediately
  before that individual drag.
"""

from dataclasses import dataclass
import hashlib
import json
from typing import Union

from .actions import FantasyPlacementAction, NormalPlacementAction, enumerate_normal_actions
from .state import Card, OFCState, PendingPlacement, ROW_CAPACITY, Row


RUNTIME_TURN_PLAN_SCHEMA_VERSION = 1
StrategyAction = Union[NormalPlacementAction, FantasyPlacementAction]


@dataclass(frozen=True)
class RuntimePlacement:
    card_code: str
    row: Row

    def to_payload(self) -> dict[str, str]:
        return {"card": self.card_code, "row": self.row.value}


@dataclass(frozen=True)
class RuntimeTurnPlan:
    """Pure semantic turn plan; contains no screen coordinates or mouse input."""

    schema_version: int
    decision_fingerprint: str
    mode: str
    player_count: int
    hero_chair: int
    dealer_chair: int
    acting_chair: int
    round_index: int
    fantasy: bool
    incoming_cards: tuple[str, ...]
    target_placements: tuple[RuntimePlacement, ...]
    already_correct: tuple[RuntimePlacement, ...]
    placements_to_add: tuple[RuntimePlacement, ...]
    unused_cards: tuple[str, ...]
    confirm_required: bool = True

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "decision_fingerprint": self.decision_fingerprint,
            "mode": self.mode,
            "player_count": self.player_count,
            "hero_chair": self.hero_chair,
            "dealer_chair": self.dealer_chair,
            "acting_chair": self.acting_chair,
            "round_index": self.round_index,
            "fantasy": self.fantasy,
            "incoming_cards": list(self.incoming_cards),
            "target_placements": [p.to_payload() for p in self.target_placements],
            "already_correct": [p.to_payload() for p in self.already_correct],
            "placements_to_add": [p.to_payload() for p in self.placements_to_add],
            "unused_cards": list(self.unused_cards),
            "confirm_required": self.confirm_required,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_payload(), sort_keys=True, separators=(",", ":"))


def _sorted_codes(cards: tuple[Card, ...] | list[Card]) -> tuple[str, ...]:
    return tuple(sorted(card.code for card in cards))


def _board_payload(state: OFCState) -> list[dict[str, object]]:
    players: list[dict[str, object]] = []
    for player in sorted(state.players, key=lambda p: p.chair):
        players.append(
            {
                "chair": player.chair,
                "top": sorted(card.code for card in player.board.top),
                "middle": sorted(card.code for card in player.board.middle),
                "bottom": sorted(card.code for card in player.board.bottom),
                "fantasy": player.fantasy,
                "sitting_out": player.sitting_out,
                "hidden_discard_count": player.hidden_discard_count,
                "hidden_incoming_count": player.hidden_incoming_count,
            }
        )
    return players


def strategic_decision_payload(state: OFCState) -> dict[str, object]:
    """Canonical strategy-relevant snapshot used to bind a solver response.

    Tentative `hero_pending` and UI-only prepare/confirm flags are deliberately
    excluded.  A drag that merely moves one current incoming card to its target
    row must not invalidate the solver action for the same strategic decision.
    Opponent boards/counts, acting order, Hero incoming/discards and every
    physical Joker identity are included.
    """

    return {
        "mode": state.mode,
        "players": _board_payload(state),
        "hero_chair": state.hero_chair,
        "dealer_chair": state.dealer_chair,
        "acting_chair": state.acting_chair,
        "round_index": state.round_index,
        "hero_incoming": list(_sorted_codes(list(state.hero_incoming))),
        "hero_discards": list(_sorted_codes(list(state.hero_discards))),
    }


def strategic_decision_fingerprint(state: OFCState) -> str:
    raw = json.dumps(
        strategic_decision_payload(state),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _placement_sort_key(p: RuntimePlacement) -> tuple[int, str]:
    order = {Row.TOP: 0, Row.MIDDLE: 1, Row.BOTTOM: 2}
    return (order[p.row], p.card_code)


def _target_map(action: StrategyAction) -> dict[Card, Row]:
    result: dict[Card, Row] = {}
    for placement in action.placements:
        if placement.card in result:
            raise ValueError("strategy action places one physical card more than once")
        result[placement.card] = placement.row
    return result


def _validate_normal_action(state: OFCState, action: NormalPlacementAction) -> None:
    if state.hero_is_fantasy:
        raise ValueError("normal strategy action cannot be used in Fantasy")
    legal_keys = {candidate.key() for candidate in enumerate_normal_actions(state)}
    if action.key() not in legal_keys:
        raise ValueError("normal strategy action is not legal for this canonical state")


def _validate_fantasy_action(state: OFCState, action: FantasyPlacementAction) -> None:
    if not state.hero_is_fantasy or state.round_index != -1:
        raise ValueError("Fantasy strategy action requires a Hero Fantasy state")
    if state.player(state.hero_chair).board.filled_count() != 0:
        raise ValueError("Fantasy strategy action requires an empty committed Hero board")
    incoming = set(state.hero_incoming)
    action_cards = set(action.placed_cards) | set(action.discards)
    if action_cards != incoming:
        raise ValueError("Fantasy strategy action must partition exactly the current incoming cards")
    if len(action.placements) != 13:
        raise ValueError("Fantasy strategy action must place exactly 13 cards")
    counts = {row: 0 for row in Row}
    for placement in action.placements:
        counts[placement.row] += 1
    if counts != {Row.TOP: 3, Row.MIDDLE: 5, Row.BOTTOM: 5}:
        raise ValueError("Fantasy strategy action must target rows exactly 3/5/5")


def build_runtime_turn_plan(state: OFCState, action: StrategyAction) -> RuntimeTurnPlan:
    """Translate one solver/policy action into a fail-closed physical turn plan.

    The caller may execute `placements_to_add` sequentially through the R10
    single-drag transaction executor.  Source rectangles are intentionally not
    present and must be rescraped for each drag.

    The current R10 layer cannot yet pick a tentatively placed card back up and
    reroute it.  Therefore any current pending placement that disagrees with the
    solver action causes an immediate refusal rather than silently accepting the
    UI's provisional choice.
    """

    if not state.action_required:
        raise ValueError("runtime turn plan requires an actionable Hero decision state")
    if state.acting_chair != state.hero_chair or not state.hero_can_confirm:
        raise ValueError("runtime turn plan requires Hero to be the confirmed acting chair")

    if isinstance(action, NormalPlacementAction):
        _validate_normal_action(state, action)
        unused = () if action.discard is None else (action.discard,)
    elif isinstance(action, FantasyPlacementAction):
        _validate_fantasy_action(state, action)
        unused = tuple(action.discards)
    else:
        raise TypeError(f"unsupported strategy action type: {type(action)!r}")

    target = _target_map(action)
    incoming = set(state.hero_incoming)
    if not set(target).issubset(incoming):
        raise ValueError("strategy action contains a placement outside Hero incoming cards")
    if set(unused) & set(target):
        raise ValueError("strategy action cannot both place and leave a physical card unused")
    if set(target) | set(unused) != incoming:
        raise ValueError("strategy action must account for every current incoming physical card")

    current_pending: dict[Card, Row] = {}
    for pending in state.hero_pending:
        if pending.card in current_pending:
            raise ValueError("canonical state contains duplicate pending physical card")
        current_pending[pending.card] = pending.row

    already_correct: list[RuntimePlacement] = []
    for card, current_row in current_pending.items():
        target_row = target.get(card)
        if target_row is None:
            raise ValueError(
                f"pending card {card.code} must be unused by strategy action; rearrangement is not certified"
            )
        if target_row != current_row:
            raise ValueError(
                f"pending card {card.code} is in {current_row.value} but strategy requires {target_row.value}; rearrangement is not certified"
            )
        already_correct.append(RuntimePlacement(card.code, current_row))

    placements_to_add = [
        RuntimePlacement(card.code, row)
        for card, row in target.items()
        if card not in current_pending
    ]
    target_placements = [RuntimePlacement(card.code, row) for card, row in target.items()]

    # Final capacity check, independent of action generators and safe for both
    # normal and Fantasy callers.
    committed = state.player(state.hero_chair).board
    additions = {row: 0 for row in Row}
    for row in target.values():
        additions[row] += 1
    for row in Row:
        if len(committed.row(row)) + additions[row] > ROW_CAPACITY[row]:
            raise ValueError(f"strategy target overflows {row.value} row")

    return RuntimeTurnPlan(
        schema_version=RUNTIME_TURN_PLAN_SCHEMA_VERSION,
        decision_fingerprint=strategic_decision_fingerprint(state),
        mode=state.mode,
        player_count=len(state.players),
        hero_chair=state.hero_chair,
        dealer_chair=state.dealer_chair,
        acting_chair=state.acting_chair,
        round_index=state.round_index,
        fantasy=state.hero_is_fantasy,
        incoming_cards=_sorted_codes(list(state.hero_incoming)),
        target_placements=tuple(sorted(target_placements, key=_placement_sort_key)),
        already_correct=tuple(sorted(already_correct, key=_placement_sort_key)),
        placements_to_add=tuple(sorted(placements_to_add, key=_placement_sort_key)),
        unused_cards=_sorted_codes(list(unused)),
        confirm_required=True,
    )
