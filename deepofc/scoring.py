from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Iterable, Sequence

from .state import Card, PlayerBoard, Row


class HandCategory(IntEnum):
    HIGH_CARD = 0
    PAIR = 1
    TWO_PAIR = 2
    TRIPS = 3
    STRAIGHT = 4
    FLUSH = 5
    FULL_HOUSE = 6
    QUADS = 7
    STRAIGHT_FLUSH = 8


@dataclass(frozen=True, order=True)
class HandRank:
    category: HandCategory
    tiebreak: tuple[int, ...]


@dataclass(frozen=True)
class PairwiseScore:
    """Raw OFC points from Hero's perspective, before money/rake/win-cap.

    This object deliberately stops before KKPoker cash settlement. R1 still has
    an unresolved ordered win-cap algorithm and exact OFC rake attribution.
    """

    top_points: int
    middle_points: int
    bottom_points: int
    scoop_bonus: int
    hero_royalties: int
    opponent_royalties: int
    hero_foul: bool
    opponent_foul: bool

    @property
    def row_points(self) -> int:
        return self.top_points + self.middle_points + self.bottom_points

    @property
    def royalty_difference(self) -> int:
        return self.hero_royalties - self.opponent_royalties

    @property
    def total_points(self) -> int:
        return self.row_points + self.scoop_bonus + self.royalty_difference


TOP_PAIR_ROYALTY = {
    6: 1,
    7: 2,
    8: 3,
    9: 4,
    10: 5,
    11: 6,
    12: 7,
    13: 8,
    14: 9,
}

TOP_TRIPS_ROYALTY = {rank: rank + 8 for rank in range(2, 15)}

MIDDLE_ROYALTY_BY_CATEGORY = {
    HandCategory.TRIPS: 2,
    HandCategory.STRAIGHT: 4,
    HandCategory.FLUSH: 8,
    HandCategory.FULL_HOUSE: 12,
    HandCategory.QUADS: 20,
    HandCategory.STRAIGHT_FLUSH: 30,
}

BOTTOM_ROYALTY_BY_CATEGORY = {
    HandCategory.STRAIGHT: 2,
    HandCategory.FLUSH: 4,
    HandCategory.FULL_HOUSE: 6,
    HandCategory.QUADS: 10,
    HandCategory.STRAIGHT_FLUSH: 15,
}


def _require_standard(cards: Sequence[Card], expected: int) -> None:
    if len(cards) != expected:
        raise ValueError(f"expected {expected} cards, got {len(cards)}")
    if any(c.is_joker for c in cards):
        raise NotImplementedError(
            "Joker evaluation is deliberately blocked until R1 freezes wildcard semantics"
        )


def _straight_high(ranks: Iterable[int]) -> int | None:
    uniq = sorted(set(ranks))
    if len(uniq) != 5:
        return None
    if uniq == [2, 3, 4, 5, 14]:
        return 5
    if uniq[-1] - uniq[0] == 4:
        return uniq[-1]
    return None


def rank_top(cards: Sequence[Card]) -> HandRank:
    _require_standard(cards, 3)
    ranks = sorted((int(c.rank) for c in cards), reverse=True)
    counts = {r: ranks.count(r) for r in set(ranks)}
    grouped = sorted(((n, r) for r, n in counts.items()), reverse=True)
    if grouped[0][0] == 3:
        return HandRank(HandCategory.TRIPS, (grouped[0][1],))
    if grouped[0][0] == 2:
        pair = grouped[0][1]
        kicker = max(r for r in ranks if r != pair)
        return HandRank(HandCategory.PAIR, (pair, kicker))
    return HandRank(HandCategory.HIGH_CARD, tuple(ranks))


def rank_five(cards: Sequence[Card]) -> HandRank:
    _require_standard(cards, 5)
    ranks = [int(c.rank) for c in cards]
    suits = [str(c.suit) for c in cards]
    counts = {r: ranks.count(r) for r in set(ranks)}
    grouped = sorted(((n, r) for r, n in counts.items()), reverse=True)
    straight_high = _straight_high(ranks)
    flush = len(set(suits)) == 1

    if straight_high is not None and flush:
        return HandRank(HandCategory.STRAIGHT_FLUSH, (straight_high,))
    if grouped[0][0] == 4:
        quad = grouped[0][1]
        kicker = max(r for r in ranks if r != quad)
        return HandRank(HandCategory.QUADS, (quad, kicker))
    if grouped[0][0] == 3 and grouped[1][0] == 2:
        return HandRank(HandCategory.FULL_HOUSE, (grouped[0][1], grouped[1][1]))
    if flush:
        return HandRank(HandCategory.FLUSH, tuple(sorted(ranks, reverse=True)))
    if straight_high is not None:
        return HandRank(HandCategory.STRAIGHT, (straight_high,))
    if grouped[0][0] == 3:
        trips = grouped[0][1]
        kickers = sorted((r for r in ranks if r != trips), reverse=True)
        return HandRank(HandCategory.TRIPS, (trips, *kickers))
    if grouped[0][0] == 2 and grouped[1][0] == 2:
        pairs = sorted((grouped[0][1], grouped[1][1]), reverse=True)
        kicker = max(r for r in ranks if r not in pairs)
        return HandRank(HandCategory.TWO_PAIR, (*pairs, kicker))
    if grouped[0][0] == 2:
        pair = grouped[0][1]
        kickers = sorted((r for r in ranks if r != pair), reverse=True)
        return HandRank(HandCategory.PAIR, (pair, *kickers))
    return HandRank(HandCategory.HIGH_CARD, tuple(sorted(ranks, reverse=True)))


def is_royal_flush(rank: HandRank) -> bool:
    return rank.category == HandCategory.STRAIGHT_FLUSH and rank.tiebreak == (14,)


def royalty(row: Row, rank: HandRank) -> int:
    if row == Row.TOP:
        if rank.category == HandCategory.PAIR:
            return TOP_PAIR_ROYALTY.get(rank.tiebreak[0], 0)
        if rank.category == HandCategory.TRIPS:
            return TOP_TRIPS_ROYALTY[rank.tiebreak[0]]
        return 0

    if row == Row.MIDDLE:
        if is_royal_flush(rank):
            return 50
        return MIDDLE_ROYALTY_BY_CATEGORY.get(rank.category, 0)

    if row == Row.BOTTOM:
        if is_royal_flush(rank):
            return 25
        return BOTTOM_ROYALTY_BY_CATEGORY.get(rank.category, 0)

    raise ValueError(f"unsupported row: {row}")


def completed_board_ranks(board: PlayerBoard) -> tuple[HandRank, HandRank, HandRank]:
    if not board.is_complete():
        raise ValueError("board must be complete")
    top = rank_top(board.top)
    middle = rank_five(board.middle)
    bottom = rank_five(board.bottom)
    return top, middle, bottom


def completed_board_royalties(board: PlayerBoard) -> int:
    top, middle, bottom = completed_board_ranks(board)
    return (
        royalty(Row.TOP, top)
        + royalty(Row.MIDDLE, middle)
        + royalty(Row.BOTTOM, bottom)
    )


def is_foul(board: PlayerBoard, *, equality_allowed: bool) -> bool:
    """Evaluate row ordering with an explicit equality policy.

    The supplied current-client rule says Bottom >= Middle >= Top, while the
    generic public webpage uses stricter wording. DeepOFC's target contract uses
    equality_allowed=True, but the parameter remains explicit for regression
    testing and to avoid silently changing historical evidence.
    """
    top, middle, bottom = completed_board_ranks(board)
    if equality_allowed:
        return not (bottom >= middle >= top)
    return not (bottom > middle > top)


def _compare_rank(hero: HandRank, opponent: HandRank) -> int:
    if hero > opponent:
        return 1
    if hero < opponent:
        return -1
    return 0


def pairwise_points_standard(
    hero: PlayerBoard,
    opponent: PlayerBoard,
    *,
    equality_allowed: bool = True,
) -> PairwiseScore:
    """Score two complete standard-card OFC boards exactly in raw points.

    Supported now:
    - normal row comparison;
    - royalty difference;
    - scoop bonus;
    - exactly one fouled player (automatic scoop, fouled player loses royalties).

    Deliberately unresolved/fail-closed:
    - any Joker in either board;
    - both players fouling simultaneously;
    - cash settlement/win cap/rake.
    """

    hero_ranks = completed_board_ranks(hero)
    opponent_ranks = completed_board_ranks(opponent)
    hero_foul = is_foul(hero, equality_allowed=equality_allowed)
    opponent_foul = is_foul(opponent, equality_allowed=equality_allowed)

    if hero_foul and opponent_foul:
        raise NotImplementedError(
            "both-player foul settlement is not source-frozen in R1"
        )

    hero_royalties = 0 if hero_foul else sum(
        royalty(row, rank)
        for row, rank in zip((Row.TOP, Row.MIDDLE, Row.BOTTOM), hero_ranks)
    )
    opponent_royalties = 0 if opponent_foul else sum(
        royalty(row, rank)
        for row, rank in zip((Row.TOP, Row.MIDDLE, Row.BOTTOM), opponent_ranks)
    )

    if hero_foul:
        return PairwiseScore(
            top_points=-1,
            middle_points=-1,
            bottom_points=-1,
            scoop_bonus=-3,
            hero_royalties=0,
            opponent_royalties=opponent_royalties,
            hero_foul=True,
            opponent_foul=False,
        )

    if opponent_foul:
        return PairwiseScore(
            top_points=1,
            middle_points=1,
            bottom_points=1,
            scoop_bonus=3,
            hero_royalties=hero_royalties,
            opponent_royalties=0,
            hero_foul=False,
            opponent_foul=True,
        )

    row_results = tuple(
        _compare_rank(h, o)
        for h, o in zip(hero_ranks, opponent_ranks)
    )
    scoop = 3 if row_results == (1, 1, 1) else (-3 if row_results == (-1, -1, -1) else 0)
    return PairwiseScore(
        top_points=row_results[0],
        middle_points=row_results[1],
        bottom_points=row_results[2],
        scoop_bonus=scoop,
        hero_royalties=hero_royalties,
        opponent_royalties=opponent_royalties,
        hero_foul=False,
        opponent_foul=False,
    )
