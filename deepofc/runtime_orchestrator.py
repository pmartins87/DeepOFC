from __future__ import annotations

"""Pure fail-closed orchestration for one already-chosen DeepOFC turn plan.

The strategy/policy chooses a complete canonical action once.  This module then
tracks UI progress across fresh canonical scrapes without changing that action.
It contains no pixels, coordinates, mouse primitives, timing or poker heuristics.

A caller is expected to use the returned next placement with the OpenHoldem R10
single-drag transaction layer, obtain a **fresh** raw/canonical scrape, call this
module again, and only then issue another physical mutation.
"""

from dataclasses import dataclass

from .runtime_plan import RuntimePlacement, RuntimeTurnPlan, strategic_decision_fingerprint
from .state import OFCState, Row


@dataclass(frozen=True)
class RuntimeTurnProgress:
    decision_fingerprint: str
    already_correct: tuple[RuntimePlacement, ...]
    remaining: tuple[RuntimePlacement, ...]
    ready_for_confirm: bool

    @property
    def next_placement(self) -> RuntimePlacement | None:
        return None if not self.remaining else self.remaining[0]


def _placement_key(placement: RuntimePlacement) -> tuple[str, str]:
    return (placement.card_code, placement.row.value)


def _pending_map(state: OFCState) -> dict[str, Row]:
    out: dict[str, Row] = {}
    for pending in state.hero_pending:
        code = pending.card.code
        if code in out:
            raise ValueError("canonical state contains duplicate pending physical card")
        out[code] = pending.row
    return out


def validate_runtime_turn_progress(
    state: OFCState,
    plan: RuntimeTurnPlan,
) -> RuntimeTurnProgress:
    """Validate one fresh canonical scrape against a fixed solver turn plan.

    Strategy-relevant state is fingerprint-bound.  Tentative Hero placements are
    intentionally allowed to advance, but no opponent board/count, actor/order,
    committed Hero board, incoming/discard identity or physical Joker identity
    may drift during the same turn.
    """

    if plan.schema_version != 1:
        raise ValueError(f"unsupported runtime turn-plan schema: {plan.schema_version}")
    if not state.hero_can_prepare:
        raise ValueError("Hero can no longer prepare placements")
    if state.acting_chair != state.hero_chair:
        raise ValueError("ordered acting chair drifted away from Hero")

    current_fingerprint = strategic_decision_fingerprint(state)
    if current_fingerprint != plan.decision_fingerprint:
        raise ValueError("strategy-relevant canonical state changed during fixed turn plan")

    incoming = tuple(sorted(card.code for card in state.hero_incoming))
    if incoming != plan.incoming_cards:
        raise ValueError("Hero incoming physical-card set changed during fixed turn plan")

    target: dict[str, Row] = {}
    for placement in plan.target_placements:
        if placement.card_code in target:
            raise ValueError("turn plan contains duplicate target physical card")
        target[placement.card_code] = placement.row

    unused = set(plan.unused_cards)
    if set(target) & unused:
        raise ValueError("turn plan places and leaves unused the same physical card")
    if set(target) | unused != set(plan.incoming_cards):
        raise ValueError("turn plan no longer partitions the incoming physical-card set")

    pending = _pending_map(state)
    already: list[RuntimePlacement] = []
    for code, row in pending.items():
        expected = target.get(code)
        if expected is None:
            raise ValueError(
                f"pending physical card {code} is supposed to remain unused; rearrangement is not certified"
            )
        if row != expected:
            raise ValueError(
                f"pending physical card {code} is in {row.value}, expected {expected.value}; rearrangement is not certified"
            )
        already.append(RuntimePlacement(code, row))

    remaining = [
        placement
        for placement in plan.target_placements
        if placement.card_code not in pending
    ]
    already.sort(key=_placement_key)
    remaining.sort(key=_placement_key)

    ready = not remaining
    if ready and not state.confirm_shape_is_legal():
        raise ValueError("all target placements are present but canonical Confirm shape is illegal")

    return RuntimeTurnProgress(
        decision_fingerprint=current_fingerprint,
        already_correct=tuple(already),
        remaining=tuple(remaining),
        ready_for_confirm=ready,
    )


class RuntimeTurnOrchestrator:
    """State machine for a fixed strategy action across multiple fresh scrapes.

    It never mutates the table. `advance()` only validates current progress and
    returns what the physical R10 layer may attempt next.  The plan cannot be
    replaced once the orchestrator is created; a strategic-state change requires
    abandoning this object and obtaining a new solver decision.
    """

    def __init__(self, plan: RuntimeTurnPlan) -> None:
        self._plan = plan
        self._blocked_reason: str | None = None

    @property
    def plan(self) -> RuntimeTurnPlan:
        return self._plan

    @property
    def blocked(self) -> bool:
        return self._blocked_reason is not None

    @property
    def blocked_reason(self) -> str | None:
        return self._blocked_reason

    def advance(self, fresh_state: OFCState) -> RuntimeTurnProgress:
        if self._blocked_reason is not None:
            raise RuntimeError(f"turn orchestrator is blocked: {self._blocked_reason}")
        try:
            return validate_runtime_turn_progress(fresh_state, self._plan)
        except Exception as exc:
            # Any discrepancy in an in-progress physical turn is latched.  The
            # runtime must not try a different card/row or silently re-solve on
            # an ambiguous UI state.
            self._blocked_reason = str(exc)
            raise
