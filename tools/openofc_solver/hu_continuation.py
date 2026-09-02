from __future__ import annotations

"""HU cross-hand Fantasy state plumbing.

The continuation objective is

    current_hand_points + continuation_value[next_state]

and therefore the immediate terminal score MUST use the same canonical Joker
semantics as the live DeepOFC game model.  The historical M4/M5 continuation
module originally imported ``tools/openofc_solver/engine.py`` for scoring; that
engine predates the project-frozen 2026-08-15 Joker-with-replacement rule and
can differ by real OFC points when a Joker's strongest nominal substitution
copies an already-present card.

Normal -> Fantasy qualification is likewise routed through the canonical
``deepofc.simulator`` implementation.  Existing Fantasy -> re-Fantasy deal-size
semantics remain delegated to the historical transition module until that rule
surface is independently source-reconciled; this keeps the current change
narrow and fixes the Normal x Normal strategic path without silently rewriting
Fantasy retention rules.
"""

from dataclasses import dataclass
from functools import lru_cache
from itertools import product
from typing import Mapping

from deepofc.scoring import is_foul, pairwise_points_standard
from deepofc.simulator import normal_fantasy_entry_cards as canonical_normal_fantasy_entry_cards
from deepofc.state import Card as CanonicalCard
from deepofc.state import PlayerBoard as CanonicalPlayerBoard
from engine import Board
from fantasy_transition import (
    VALID_FANTASY_COUNTS,
    VARIANT_ULTIMATE,
    transition_from_board,
)

NORMAL = 0
HU_MODES: tuple[int, ...] = (NORMAL, *VALID_FANTASY_COUNTS)
STATE_COUNT = 2 * len(HU_MODES) * len(HU_MODES)
PLAYER_EXCHANGE_ORBIT_COUNT = STATE_COUNT // 2
AUTHORITY = "EXACT_HU_CONTINUATION_STATE_TRANSITION"

# The official KKPoker rules say that each fouled player is automatically
# scooped by every opponent, but do not explicitly spell out a heads-up hand in
# which both players foul.  The canonical scorer therefore remains fail-closed
# by default.  PLAYABLE candidates may opt into the isolated net-zero
# interpretation: both players incur the same automatic scoop against each
# other, neither earns royalties/Fantasy, and the pairwise net is zero.  Keeping
# this policy explicit makes it replaceable without rewriting scoring rules.
BOTH_FOUL_FAIL_CLOSED = "FAIL_CLOSED_UNRESOLVED"
BOTH_FOUL_NET_ZERO_INFERENCE = "MUTUAL_AUTO_SCOOP_NET_ZERO_INFERENCE"
VALID_BOTH_FOUL_POLICIES = (
    BOTH_FOUL_FAIL_CLOSED,
    BOTH_FOUL_NET_ZERO_INFERENCE,
)

KERNEL_NORMAL_NORMAL = "NORMAL_NORMAL"
KERNEL_NORMAL_FANTASY = "NORMAL_FANTASY_ASYMMETRIC"
KERNEL_FANTASY_FANTASY = "FANTASY_FANTASY"


@dataclass(frozen=True, order=True)
class HUContinuationState:
    """State carried from one HU hand to the next.

    ``button`` is the persistent player who owns the dealer/button in that hand.
    Fantasy counts are 0 for normal play or one of 14/15/16/17.
    """

    button: int
    p0_fantasy_cards: int = NORMAL
    p1_fantasy_cards: int = NORMAL

    def __post_init__(self) -> None:
        if self.button not in (0, 1):
            raise ValueError("HU button must be player 0 or player 1")
        if self.p0_fantasy_cards not in HU_MODES:
            raise ValueError("invalid player-0 Fantasy mode")
        if self.p1_fantasy_cards not in HU_MODES:
            raise ValueError("invalid player-1 Fantasy mode")

    def mode_for(self, player: int) -> int:
        if player == 0:
            return self.p0_fantasy_cards
        if player == 1:
            return self.p1_fantasy_cards
        raise ValueError("HU player must be 0 or 1")

    def as_key(self) -> str:
        return (
            f"B{self.button}:P0F{self.p0_fantasy_cards}:"
            f"P1F{self.p1_fantasy_cards}"
        )


def all_states() -> tuple[HUContinuationState, ...]:
    states = tuple(
        HUContinuationState(button, p0_mode, p1_mode)
        for button, p0_mode, p1_mode in product((0, 1), HU_MODES, HU_MODES)
    )
    if len(states) != STATE_COUNT or len(set(states)) != STATE_COUNT:
        raise AssertionError("HU continuation catalog must contain 50 states")
    return states


def hand_kernel_kind(state: HUContinuationState) -> str:
    f0 = state.p0_fantasy_cards > 0
    f1 = state.p1_fantasy_cards > 0
    if not f0 and not f1:
        return KERNEL_NORMAL_NORMAL
    if f0 != f1:
        return KERNEL_NORMAL_FANTASY
    return KERNEL_FANTASY_FANTASY


def identity_for_role(state: HUContinuationState, role: int) -> int:
    """Map relative one-hand role 0=nondealer, 1=dealer to persistent identity."""
    if role == 0:
        return 1 - state.button
    if role == 1:
        return state.button
    raise ValueError("HU role must be 0=nondealer or 1=dealer")


def role_for_identity(state: HUContinuationState, player: int) -> int:
    if player not in (0, 1):
        raise ValueError("HU player must be 0 or 1")
    return 1 if player == state.button else 0


def modes_in_role_order(state: HUContinuationState) -> tuple[int, int]:
    return (
        state.mode_for(identity_for_role(state, 0)),
        state.mode_for(identity_for_role(state, 1)),
    )


def utility_from_nondealer_perspective_to_p0(
    state: HUContinuationState,
    nondealer_utility: float,
) -> float:
    return (
        float(nondealer_utility)
        if identity_for_role(state, 0) == 0
        else -float(nondealer_utility)
    )


def swap_players(state: HUContinuationState) -> HUContinuationState:
    return HUContinuationState(
        button=1 - state.button,
        p0_fantasy_cards=state.p1_fantasy_cards,
        p1_fantasy_cards=state.p0_fantasy_cards,
    )


def canonical_player_exchange(
    state: HUContinuationState,
) -> tuple[HUContinuationState, int]:
    partner = swap_players(state)
    if state <= partner:
        return state, 1
    return partner, -1


def canonical_states() -> tuple[HUContinuationState, ...]:
    representatives = tuple(sorted({canonical_player_exchange(s)[0] for s in all_states()}))
    if len(representatives) != PLAYER_EXCHANGE_ORBIT_COUNT:
        raise AssertionError("HU player exchange must reduce 50 states to 25 orbits")
    return representatives


def expand_antisymmetric_values(
    canonical_values: Mapping[HUContinuationState, float],
) -> dict[HUContinuationState, float]:
    reps = canonical_states()
    missing = [state for state in reps if state not in canonical_values]
    if missing:
        raise ValueError(f"canonical continuation map is incomplete: {len(missing)} missing")
    out: dict[HUContinuationState, float] = {}
    for state in all_states():
        canonical, sign = canonical_player_exchange(state)
        out[state] = sign * float(canonical_values[canonical])
    return out


def default_next_button(current_button: int) -> int:
    if current_button not in (0, 1):
        raise ValueError("HU button must be player 0 or player 1")
    return 1 - current_button


@lru_cache(maxsize=250_000)
def _canonical_board(board: Board) -> CanonicalPlayerBoard:
    """Convert the migrated solver Board into the canonical physical-card board."""

    def convert_row(cards) -> tuple[CanonicalCard, ...]:
        return tuple(CanonicalCard.from_code(str(card)) for card in cards)

    return CanonicalPlayerBoard(
        top=convert_row(board.top),
        middle=convert_row(board.middle),
        bottom=convert_row(board.bottom),
    )


@lru_cache(maxsize=250_000)
def canonical_terminal_points_p0(
    board0: Board,
    board1: Board,
    *,
    both_foul_policy: str = BOTH_FOUL_FAIL_CLOSED,
) -> int:
    """Canonical raw hand points from persistent player 0's perspective.

    This is intentionally a thin adapter around ``deepofc.scoring`` so every
    continuation-aware strategic kernel shares the same with-replacement Joker,
    board-aware foul, royalty and scoop semantics as the canonical simulator.
    Simultaneous both-foul remains fail-closed in that source of truth.
    """

    if both_foul_policy not in VALID_BOTH_FOUL_POLICIES:
        raise ValueError(f"unsupported both-foul settlement policy: {both_foul_policy}")
    canonical0 = _canonical_board(board0)
    canonical1 = _canonical_board(board1)
    try:
        score = pairwise_points_standard(
            canonical0,
            canonical1,
            equality_allowed=True,
        )
    except NotImplementedError:
        if not (
            is_foul(canonical0, equality_allowed=True)
            and is_foul(canonical1, equality_allowed=True)
        ):
            raise
        if both_foul_policy == BOTH_FOUL_NET_ZERO_INFERENCE:
            return 0
        raise
    return int(score.total_points)


def _next_fantasy_cards(
    board: Board,
    *,
    current_fantasy_cards: int,
    variant: str,
) -> int:
    """Return next mode while keeping the current change source-narrow.

    Normal-hand entry uses the canonical DeepOFC rule (QQ=14, KK=15, AA=16,
    Top trips=17 after board-aware Joker resolution).  Re-Fantasy retention is
    left on the migrated transition contract for now because its exact Ultimate
    deal-size rule is a separate source question and is not needed to correct
    the first playable Normal x Normal route.
    """

    if current_fantasy_cards == NORMAL:
        next_cards = canonical_normal_fantasy_entry_cards(
            _canonical_board(board),
            equality_allowed=True,
        )
        return NORMAL if next_cards is None else int(next_cards)
    return int(
        transition_from_board(
            board,
            current_fantasy_cards=current_fantasy_cards,
            variant=variant,
        ).next_cards
    )


def next_state_from_terminal_boards(
    current: HUContinuationState,
    board0: Board,
    board1: Board,
    *,
    next_button: int | None = None,
    variant: str = VARIANT_ULTIMATE,
) -> HUContinuationState:
    """Apply the terminal qualification transition for both persistent players."""

    p0_next = _next_fantasy_cards(
        board0,
        current_fantasy_cards=current.p0_fantasy_cards,
        variant=variant,
    )
    p1_next = _next_fantasy_cards(
        board1,
        current_fantasy_cards=current.p1_fantasy_cards,
        variant=variant,
    )
    button = (
        default_next_button(current.button)
        if next_button is None
        else int(next_button)
    )
    return HUContinuationState(
        button=button,
        p0_fantasy_cards=p0_next,
        p1_fantasy_cards=p1_next,
    )


def continuation_adjusted_terminal_utility(
    current: HUContinuationState,
    board0: Board,
    board1: Board,
    continuation_values: Mapping[HUContinuationState, float],
    *,
    update_player: int = 0,
    next_button: int | None = None,
    variant: str = VARIANT_ULTIMATE,
    both_foul_policy: str = BOTH_FOUL_FAIL_CLOSED,
) -> float:
    """Exact one-step Bellman backup conditional on the supplied continuation vector."""

    if update_player not in (0, 1):
        raise ValueError("HU player must be 0 or 1")
    nxt = next_state_from_terminal_boards(
        current,
        board0,
        board1,
        next_button=next_button,
        variant=variant,
    )
    if nxt not in continuation_values:
        raise KeyError(f"continuation value missing for {nxt.as_key()}")
    immediate_p0 = float(
        canonical_terminal_points_p0(
            board0,
            board1,
            both_foul_policy=both_foul_policy,
        )
    )
    total_p0 = immediate_p0 + float(continuation_values[nxt])
    return total_p0 if update_player == 0 else -total_p0


def zero_continuation_values() -> dict[HUContinuationState, float]:
    return {state: 0.0 for state in all_states()}


def normalize_relative_values(
    raw_values: Mapping[HUContinuationState, float],
    *,
    reference: HUContinuationState | None = None,
) -> tuple[float, dict[HUContinuationState, float]]:
    states = all_states()
    missing = [state for state in states if state not in raw_values]
    if missing:
        raise ValueError(
            f"relative-value image is incomplete: {len(missing)} states missing"
        )
    if reference is None:
        reference = HUContinuationState(0, NORMAL, NORMAL)
    if reference not in raw_values:
        raise ValueError("reference state missing from relative-value image")
    anchor = float(raw_values[reference])
    normalized = {
        state: float(raw_values[state]) - anchor
        for state in states
    }
    return anchor, normalized
