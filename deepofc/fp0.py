from __future__ import annotations

"""Single-call strategy-to-runtime bridge for the first playable simulator.

This is the temporary FP0 entry point used while the trained External Sampling
blueprint is not yet available.  It deliberately composes existing layers
instead of duplicating them:

canonical OFC state -> quality-aware baseline -> validated RuntimeTurnPlan

The returned plan still contains no screen coordinates.  R10 must resolve a
fresh physical source rectangle before every drag and rescrape after it.
"""

from dataclasses import dataclass

from .baseline import BaselineDecision, choose_baseline_decision
from .runtime_plan import RuntimeTurnPlan, build_runtime_turn_plan
from .state import OFCState


@dataclass(frozen=True)
class FP0PreparedTurn:
    decision: BaselineDecision
    plan: RuntimeTurnPlan


def prepare_fp0_turn(
    state: OFCState,
    *,
    equality_allowed: bool = True,
) -> FP0PreparedTurn:
    """Choose the temporary FP0 policy action and bind it to the exact state."""

    decision = choose_baseline_decision(
        state,
        equality_allowed=equality_allowed,
    )
    plan = build_runtime_turn_plan(state, decision.action)
    return FP0PreparedTurn(decision=decision, plan=plan)
