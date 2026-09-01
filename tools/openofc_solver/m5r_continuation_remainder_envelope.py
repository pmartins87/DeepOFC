from __future__ import annotations

"""Conservative continuation-aware P0 remainder envelopes for M5R.

The existing raw-point envelope bounds only the current hand.  A certification-
facing normal/normal best-response interval must bound the exact Bellman terminal
objective

    current_hand_points + V(next_hu_state)

at every pruned subtree.  This module adds a deliberately broad but rigorous
continuation range to the audited raw-point interval.  It does not infer Fantasy
qualification from an incomplete board; instead it enumerates every next mode
that is legally possible from the current cross-hand mode under Ultimate rules.
"""

from dataclasses import dataclass
import math
from typing import Mapping

from deepofc.state import PlayerBoard
from hu_continuation import (
    HUContinuationState,
    HU_MODES,
    NORMAL,
    all_states,
    default_next_button,
)
from m5r_full_game_remainder_envelope import p0_raw_point_interval

AUTHORITY = "M5R_CONSERVATIVE_CONTINUATION_REMAINDER_ENVELOPE_NOT_CERTIFICATION"
SCHEMA = "openofc-m5r-continuation-remainder-envelope-v1"


@dataclass(frozen=True)
class ContinuationRemainderEnvelope:
    current_state: HUContinuationState
    raw_lower: float
    raw_upper: float
    continuation_lower: float
    continuation_upper: float
    lower: float
    upper: float
    candidate_next_states: tuple[HUContinuationState, ...]
    authority: str = AUTHORITY
    schema: str = SCHEMA

    @property
    def raw_width(self) -> float:
        return self.raw_upper - self.raw_lower

    @property
    def continuation_width(self) -> float:
        return self.continuation_upper - self.continuation_lower

    @property
    def width(self) -> float:
        return self.upper - self.lower


def possible_next_fantasy_modes(current_fantasy_cards: int) -> tuple[int, ...]:
    """Return a safe exact mode superset before terminal board qualification.

    In normal play a completed Ultimate board may fail to enter Fantasy or enter
    with 14/15/16/17 cards.  While already in Fantasy, the next hand either
    leaves Fantasy or requalifies at the same deal size.  No other next mode is
    reachable from the current cross-hand state.
    """

    current = int(current_fantasy_cards)
    if current == NORMAL:
        return tuple(HU_MODES)
    if current not in HU_MODES:
        raise ValueError("invalid current Fantasy mode")
    return (NORMAL, current)


def candidate_next_states(current: HUContinuationState) -> tuple[HUContinuationState, ...]:
    """Enumerate every next HU state that can be reached from incomplete boards.

    The set is conservative with respect to incomplete-board information: some
    candidates can later become impossible as rows fill, but no legal terminal
    next state is omitted.
    """

    next_button = default_next_button(current.button)
    p0_modes = possible_next_fantasy_modes(current.p0_fantasy_cards)
    p1_modes = possible_next_fantasy_modes(current.p1_fantasy_cards)
    states = tuple(
        HUContinuationState(next_button, p0_mode, p1_mode)
        for p0_mode in p0_modes
        for p1_mode in p1_modes
    )
    if not states or len(states) != len(set(states)):
        raise AssertionError("continuation candidate-state enumeration is invalid")
    return states


def _validated_values(
    continuation_values: Mapping[HUContinuationState, float],
) -> dict[HUContinuationState, float]:
    required = set(all_states())
    supplied = set(continuation_values)
    if supplied != required:
        missing = sorted(state.as_key() for state in required - supplied)
        extra = sorted(state.as_key() for state in supplied - required)
        raise ValueError(
            "continuation envelope requires the complete 50-state vector; "
            f"missing={missing[:3]} extra={extra[:3]}"
        )
    out: dict[HUContinuationState, float] = {}
    for state in required:
        value = float(continuation_values[state])
        if not math.isfinite(value):
            raise ValueError(f"non-finite continuation value for {state.as_key()}")
        out[state] = value
    return out


def continuation_remainder_envelope(
    current: HUContinuationState,
    continuation_values: Mapping[HUContinuationState, float],
    p0_board: PlayerBoard,
    p1_board: PlayerBoard,
) -> ContinuationRemainderEnvelope:
    """Bound P0 current-hand points plus continuation value from partial boards."""

    values = _validated_values(continuation_values)
    raw_lo, raw_hi = p0_raw_point_interval(p0_board, p1_board)
    candidates = candidate_next_states(current)
    continuation = tuple(values[state] for state in candidates)
    cont_lo = min(continuation)
    cont_hi = max(continuation)
    lower = float(raw_lo) + cont_lo
    upper = float(raw_hi) + cont_hi
    if lower > upper:
        raise AssertionError("continuation remainder envelope is inverted")
    return ContinuationRemainderEnvelope(
        current_state=current,
        raw_lower=float(raw_lo),
        raw_upper=float(raw_hi),
        continuation_lower=cont_lo,
        continuation_upper=cont_hi,
        lower=lower,
        upper=upper,
        candidate_next_states=candidates,
    )


def p0_continuation_point_interval(
    current: HUContinuationState,
    continuation_values: Mapping[HUContinuationState, float],
    p0_board: PlayerBoard,
    p1_board: PlayerBoard,
) -> tuple[float, float]:
    """State-interval callback surface consumed by conservative BR traversals."""

    envelope = continuation_remainder_envelope(
        current, continuation_values, p0_board, p1_board
    )
    return envelope.lower, envelope.upper
