from __future__ import annotations

"""Rigorous state-local raw-point remainder envelopes for full OpenOFC boards.

This module deliberately bounds the *terminal raw OFC point utility* only.  It
contains no learned value estimate, no search heuristic, and no route-promotion
logic.  The bound is derived from the frozen scoring implementation and is safe
for every scorable completion of two canonical partial ``PlayerBoard`` objects.

The current scoring contract deliberately fails closed when both players foul.
Such a terminal has no defined raw settlement yet, so this module also fails
closed when the supplied complete boards are both fouled.  For incomplete
boards, the envelope ranges over all completions for which the existing scoring
primitive is defined; it never invents a both-foul settlement.
"""

from dataclasses import dataclass
from itertools import product

from deepofc.scoring import (
    BOTTOM_ROYALTY_BY_CATEGORY,
    MIDDLE_ROYALTY_BY_CATEGORY,
    TOP_PAIR_ROYALTY,
    TOP_TRIPS_ROYALTY,
    completed_board_royalties,
    is_foul,
    pairwise_points_standard,
    rank_five,
    rank_top,
    royalty,
)
from deepofc.simulator import PHYSICAL_DECK_54
from deepofc.state import PlayerBoard, ROW_CAPACITY, Row

SCHEMA = "openofc-m5r-full-game-state-local-remainder-envelope-v1"
AUTHORITY = "RIGOROUS_SCORING_DERIVED_REMAINDER_ENVELOPE_NOT_ROUTE_CERTIFICATION"

MAX_TOP_ROYALTY = max((*TOP_PAIR_ROYALTY.values(), *TOP_TRIPS_ROYALTY.values()))
MAX_MIDDLE_ROYALTY = max(50, *MIDDLE_ROYALTY_BY_CATEGORY.values())
MAX_BOTTOM_ROYALTY = max(25, *BOTTOM_ROYALTY_BY_CATEGORY.values())
MAX_BOARD_ROYALTY = MAX_TOP_ROYALTY + MAX_MIDDLE_ROYALTY + MAX_BOTTOM_ROYALTY
MAX_ROW_PLUS_SCOOP_ABS = 6
GLOBAL_RAW_POINT_ABS_BOUND = MAX_ROW_PLUS_SCOOP_ABS + MAX_BOARD_ROYALTY

ROW_ROYALTY_CAP = {
    Row.TOP: MAX_TOP_ROYALTY,
    Row.MIDDLE: MAX_MIDDLE_ROYALTY,
    Row.BOTTOM: MAX_BOTTOM_ROYALTY,
}

STATUS_NONFOUL = "NONFOUL"
STATUS_FOUL = "FOUL"
STATUS_UNKNOWN = "UNKNOWN"


class UndefinedBothFoulSettlement(NotImplementedError):
    """Raised when the existing scoring contract has no terminal utility."""


@dataclass(frozen=True)
class RawPointRemainderEnvelope:
    lower_raw_points: int
    upper_raw_points: int
    hero_nonfoul_royalty_lower: int
    hero_nonfoul_royalty_upper: int
    opponent_nonfoul_royalty_lower: int
    opponent_nonfoul_royalty_upper: int
    both_nonfoul_base_lower: int
    both_nonfoul_base_upper: int
    hero_foul_status: str
    opponent_foul_status: str
    fixed_nonfoul_row_results: tuple[int | None, int | None, int | None]
    scenario_labels: tuple[str, ...]
    exact_terminal: bool
    global_raw_point_abs_bound: int = GLOBAL_RAW_POINT_ABS_BOUND
    schema: str = SCHEMA
    authority: str = AUTHORITY
    production_certification_eligible: bool = False
    real_routes_certified: int = 0

    def __post_init__(self) -> None:
        if self.lower_raw_points > self.upper_raw_points:
            raise ValueError("state-local remainder envelope is inverted")
        if self.lower_raw_points < -GLOBAL_RAW_POINT_ABS_BOUND:
            raise AssertionError("state-local lower bound escaped global scoring bound")
        if self.upper_raw_points > GLOBAL_RAW_POINT_ABS_BOUND:
            raise AssertionError("state-local upper bound escaped global scoring bound")

    @property
    def width(self) -> int:
        return self.upper_raw_points - self.lower_raw_points

    def contains(self, raw_points: float, *, atol: float = 1e-12) -> bool:
        value = float(raw_points)
        return (
            value >= float(self.lower_raw_points) - atol
            and value <= float(self.upper_raw_points) + atol
        )


def _validate_board_pair(hero: PlayerBoard, opponent: PlayerBoard) -> None:
    cards = (*hero.cards(), *opponent.cards())
    if len(cards) != len(set(cards)):
        raise ValueError("duplicate physical card across remainder-envelope boards")
    physical = set(PHYSICAL_DECK_54)
    if any(card not in physical for card in cards):
        raise ValueError("remainder-envelope board contains non-physical card")


def _foul_status(board: PlayerBoard, *, equality_allowed: bool) -> str:
    if not board.is_complete():
        return STATUS_UNKNOWN
    return STATUS_FOUL if is_foul(board, equality_allowed=equality_allowed) else STATUS_NONFOUL


def _fixed_row_rank(board: PlayerBoard, row: Row):
    cards = board.row(row)
    if len(cards) != ROW_CAPACITY[row] or any(card.is_joker for card in cards):
        return None
    if row == Row.TOP:
        return rank_top(cards)
    return rank_five(cards)


def _nonfoul_royalty_interval(board: PlayerBoard, *, equality_allowed: bool) -> tuple[int, int]:
    """Bound royalties conditional on this board finishing non-fouled.

    A completed non-fouled board has exact board-aware Joker royalties.  On a
    partial board, every complete non-Joker row has an immutable rank and thus an
    immutable royalty conditional on the final board remaining valid.  Any row
    that is incomplete or contains a Joker keeps the full frozen row royalty
    range [0, row_cap].  This is intentionally conservative.
    """

    if board.is_complete() and not is_foul(board, equality_allowed=equality_allowed):
        value = int(completed_board_royalties(board))
        return value, value

    lower = 0
    upper = 0
    for row in (Row.TOP, Row.MIDDLE, Row.BOTTOM):
        fixed = _fixed_row_rank(board, row)
        if fixed is None:
            upper += ROW_ROYALTY_CAP[row]
            continue
        value = int(royalty(row, fixed))
        lower += value
        upper += value
    return lower, upper


def _fixed_nonfoul_row_results(
    hero: PlayerBoard,
    opponent: PlayerBoard,
) -> tuple[int | None, int | None, int | None]:
    results: list[int | None] = []
    for row in (Row.TOP, Row.MIDDLE, Row.BOTTOM):
        hero_rank = _fixed_row_rank(hero, row)
        opponent_rank = _fixed_row_rank(opponent, row)
        if hero_rank is None or opponent_rank is None:
            results.append(None)
        elif hero_rank > opponent_rank:
            results.append(1)
        elif hero_rank < opponent_rank:
            results.append(-1)
        else:
            results.append(0)
    return tuple(results)  # type: ignore[return-value]


def _both_nonfoul_base_interval(
    fixed_results: tuple[int | None, int | None, int | None],
) -> tuple[int, int]:
    choices = [(-1, 0, 1) if result is None else (result,) for result in fixed_results]
    values: list[int] = []
    for row_results in product(*choices):
        scoop = 3 if row_results == (1, 1, 1) else (-3 if row_results == (-1, -1, -1) else 0)
        values.append(int(sum(row_results) + scoop))
    return min(values), max(values)


def _allowed_statuses(status: str) -> tuple[str, ...]:
    if status == STATUS_UNKNOWN:
        return STATUS_NONFOUL, STATUS_FOUL
    if status in (STATUS_NONFOUL, STATUS_FOUL):
        return (status,)
    raise AssertionError(f"unsupported foul status: {status}")


def raw_point_remainder_envelope(
    hero: PlayerBoard,
    opponent: PlayerBoard,
    *,
    equality_allowed: bool = True,
) -> RawPointRemainderEnvelope:
    """Return a rigorous Hero-perspective raw-point interval.

    The interval is the union of every scoring-defined foul-status scenario
    still compatible with the supplied partial boards.  In the both-nonfoul
    scenario it additionally locks any corresponding complete non-Joker row
    comparisons and complete non-Joker row royalties.
    """

    _validate_board_pair(hero, opponent)
    hero_status = _foul_status(hero, equality_allowed=equality_allowed)
    opponent_status = _foul_status(opponent, equality_allowed=equality_allowed)

    fixed_results = _fixed_nonfoul_row_results(hero, opponent)
    base_lower, base_upper = _both_nonfoul_base_interval(fixed_results)
    hero_royalty_lower, hero_royalty_upper = _nonfoul_royalty_interval(
        hero, equality_allowed=equality_allowed
    )
    opponent_royalty_lower, opponent_royalty_upper = _nonfoul_royalty_interval(
        opponent, equality_allowed=equality_allowed
    )

    if hero.is_complete() and opponent.is_complete():
        if hero_status == STATUS_FOUL and opponent_status == STATUS_FOUL:
            raise UndefinedBothFoulSettlement(
                "both-player foul settlement is not source-frozen; cannot bound an undefined utility"
            )
        exact = int(
            pairwise_points_standard(
                hero, opponent, equality_allowed=equality_allowed
            ).total_points
        )
        return RawPointRemainderEnvelope(
            lower_raw_points=exact,
            upper_raw_points=exact,
            hero_nonfoul_royalty_lower=hero_royalty_lower,
            hero_nonfoul_royalty_upper=hero_royalty_upper,
            opponent_nonfoul_royalty_lower=opponent_royalty_lower,
            opponent_nonfoul_royalty_upper=opponent_royalty_upper,
            both_nonfoul_base_lower=base_lower,
            both_nonfoul_base_upper=base_upper,
            hero_foul_status=hero_status,
            opponent_foul_status=opponent_status,
            fixed_nonfoul_row_results=fixed_results,
            scenario_labels=("EXACT_TERMINAL",),
            exact_terminal=True,
        )

    intervals: list[tuple[int, int, str]] = []
    for hero_case in _allowed_statuses(hero_status):
        for opponent_case in _allowed_statuses(opponent_status):
            if hero_case == STATUS_FOUL and opponent_case == STATUS_FOUL:
                # Existing scoring intentionally leaves this case undefined.
                continue
            if hero_case == STATUS_FOUL:
                intervals.append(
                    (
                        -6 - opponent_royalty_upper,
                        -6 - opponent_royalty_lower,
                        "HERO_FOUL_OPPONENT_NONFOUL",
                    )
                )
            elif opponent_case == STATUS_FOUL:
                intervals.append(
                    (
                        6 + hero_royalty_lower,
                        6 + hero_royalty_upper,
                        "HERO_NONFOUL_OPPONENT_FOUL",
                    )
                )
            else:
                intervals.append(
                    (
                        base_lower + hero_royalty_lower - opponent_royalty_upper,
                        base_upper + hero_royalty_upper - opponent_royalty_lower,
                        "BOTH_NONFOUL",
                    )
                )

    if not intervals:
        raise UndefinedBothFoulSettlement(
            "no scoring-defined completion remains after excluding both-foul settlement"
        )

    lower = min(row[0] for row in intervals)
    upper = max(row[1] for row in intervals)
    return RawPointRemainderEnvelope(
        lower_raw_points=int(lower),
        upper_raw_points=int(upper),
        hero_nonfoul_royalty_lower=hero_royalty_lower,
        hero_nonfoul_royalty_upper=hero_royalty_upper,
        opponent_nonfoul_royalty_lower=opponent_royalty_lower,
        opponent_nonfoul_royalty_upper=opponent_royalty_upper,
        both_nonfoul_base_lower=base_lower,
        both_nonfoul_base_upper=base_upper,
        hero_foul_status=hero_status,
        opponent_foul_status=opponent_status,
        fixed_nonfoul_row_results=fixed_results,
        scenario_labels=tuple(row[2] for row in intervals),
        exact_terminal=False,
    )


def p0_raw_point_interval(
    board0: PlayerBoard,
    board1: PlayerBoard,
    *,
    equality_allowed: bool = True,
) -> tuple[float, float]:
    """Adapter for M5R evaluators that consume a P0 utility interval callback."""

    envelope = raw_point_remainder_envelope(
        board0, board1, equality_allowed=equality_allowed
    )
    return float(envelope.lower_raw_points), float(envelope.upper_raw_points)
