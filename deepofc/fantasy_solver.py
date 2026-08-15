from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Sequence

from .actions import FantasyPlacementAction
from .scoring import (
    HandCategory,
    HandRank,
    _canonical_eval_key,
    _five_rank_candidates_cached,
    _top_rank_candidates_cached,
    completed_board_ranks,
    is_foul,
    royalty,
)
from .state import Card, OFCState, PendingPlacement, PlayerBoard, Row


@dataclass(frozen=True)
class FantasySearchStats:
    """Deterministic counters for the exact subset search."""

    incoming_cards: int
    top_subsets: int
    five_subsets: int
    bottom_middle_pairs: int
    middle_order_pruned: int
    top_partitions_tested: int
    top_order_pruned: int
    valid_boards_scored: int


@dataclass(frozen=True)
class FantasyDecision:
    """Exact current-hand optimum for a fully observed Fantasy terminal state.

    The opponent boards must already be complete/known. That makes this an exact
    terminal kernel and a regression reference for later imperfect-information
    search. It is not yet the live hidden-opponent Fantasy policy.
    """

    action: FantasyPlacementAction
    board: PlayerBoard
    resolved_ranks: tuple[HandRank, HandRank, HandRank]
    current_hand_points: int
    refantasy_qualifies: bool
    continuation_points: float
    total_value: float
    tied_best_count: int
    stats: FantasySearchStats


def _mask(indices: Sequence[int]) -> int:
    value = 0
    for index in indices:
        value |= 1 << index
    return value


def _cards_for_mask(cards: tuple[Card, ...], mask: int) -> tuple[Card, ...]:
    return tuple(card for i, card in enumerate(cards) if mask & (1 << i))


def _rank_is_not_stronger_than(
    candidate: HandRank,
    ceiling: HandRank,
    *,
    equality_allowed: bool,
) -> bool:
    return candidate <= ceiling if equality_allowed else candidate < ceiling


def _resolve_cached_candidates(
    top_candidates: tuple[HandRank, ...],
    middle_candidates: tuple[HandRank, ...],
    bottom_candidates: tuple[HandRank, ...],
    *,
    equality_allowed: bool,
) -> tuple[HandRank, HandRank, HandRank] | None:
    """Mirror the frozen board-aware Joker rule without rebuilding a board.

    Candidate tuples are already sorted strongest-first by the scoring cache.
    The strongest Bottom is always preferable. If no Middle can fit beneath the
    strongest Bottom, a weaker Bottom cannot make that constraint easier. The
    same monotonicity applies from Middle to Top.
    """

    bottom = bottom_candidates[0]
    middle = next(
        (
            candidate
            for candidate in middle_candidates
            if _rank_is_not_stronger_than(
                candidate, bottom, equality_allowed=equality_allowed
            )
        ),
        None,
    )
    if middle is None:
        return None
    top = next(
        (
            candidate
            for candidate in top_candidates
            if _rank_is_not_stronger_than(
                candidate, middle, equality_allowed=equality_allowed
            )
        ),
        None,
    )
    if top is None:
        return None
    return top, middle, bottom


def _royalties(ranks: tuple[HandRank, HandRank, HandRank]) -> int:
    return sum(
        royalty(row, rank)
        for row, rank in zip((Row.TOP, Row.MIDDLE, Row.BOTTOM), ranks)
    )


def _compare(hero: HandRank, opponent: HandRank) -> int:
    if hero > opponent:
        return 1
    if hero < opponent:
        return -1
    return 0


@dataclass(frozen=True)
class _ResolvedOpponent:
    ranks: tuple[HandRank, HandRank, HandRank]
    foul: bool
    royalties: int


def _resolve_opponent(
    board: PlayerBoard,
    *,
    equality_allowed: bool,
) -> _ResolvedOpponent:
    if not board.is_complete():
        raise ValueError("exact Fantasy terminal kernel requires complete opponent boards")
    foul = is_foul(board, equality_allowed=equality_allowed)
    ranks = completed_board_ranks(board, equality_allowed=equality_allowed)
    return _ResolvedOpponent(
        ranks=ranks,
        foul=foul,
        royalties=0 if foul else _royalties(ranks),
    )


def _score_valid_hero_ranks(
    hero_ranks: tuple[HandRank, HandRank, HandRank],
    opponents: tuple[_ResolvedOpponent, ...],
) -> int:
    """Exact raw pairwise score for a non-fouled Hero board."""

    hero_royalties = _royalties(hero_ranks)
    total = 0
    for opponent in opponents:
        if opponent.foul:
            # Valid Hero automatically wins all rows + scoop; fouled opponent
            # receives no royalties.
            total += 6 + hero_royalties
            continue
        rows = tuple(
            _compare(hero, villain)
            for hero, villain in zip(hero_ranks, opponent.ranks)
        )
        scoop = 3 if rows == (1, 1, 1) else (-3 if rows == (-1, -1, -1) else 0)
        total += sum(rows) + scoop + hero_royalties - opponent.royalties
    return total


def _refantasy_from_resolved_ranks(
    ranks: tuple[HandRank, HandRank, HandRank],
) -> bool:
    top, _, bottom = ranks
    return top.category == HandCategory.TRIPS or bottom.category >= HandCategory.QUADS


def _action_from_masks(
    incoming: tuple[Card, ...],
    *,
    top_mask: int,
    middle_mask: int,
    bottom_mask: int,
) -> tuple[FantasyPlacementAction, PlayerBoard]:
    top = _cards_for_mask(incoming, top_mask)
    middle = _cards_for_mask(incoming, middle_mask)
    bottom = _cards_for_mask(incoming, bottom_mask)
    used = top_mask | middle_mask | bottom_mask
    all_mask = (1 << len(incoming)) - 1
    discards = _cards_for_mask(incoming, all_mask ^ used)
    action = FantasyPlacementAction(
        placements=(
            *(PendingPlacement(card=card, row=Row.TOP) for card in top),
            *(PendingPlacement(card=card, row=Row.MIDDLE) for card in middle),
            *(PendingPlacement(card=card, row=Row.BOTTOM) for card in bottom),
        ),
        discards=discards,
    )
    board = PlayerBoard(top=top, middle=middle, bottom=bottom)
    return action, board


def evaluate_fantasy_exact_subsets(
    state: OFCState,
    *,
    refantasy_continuation_value: float = 0.0,
    equality_allowed: bool = True,
) -> FantasyDecision:
    """Solve a fully observed 14..17-card Fantasy placement exactly.

    This kernel precomputes every 3-card and 5-card subset rank once, then joins
    disjoint Bottom/Middle/Top masks. Joker candidate ranks are exact and use the
    same board-aware strongest-valid rule as `completed_board_ranks`.

    The function is exact in game semantics for 14..17 cards. Performance is a
    separate gate: R5 initially certifies 14-card search; larger Fantasy sizes
    must earn production status through branch-and-bound/DP benchmarks rather
    than by silently timing out.

    Opponent boards are read from canonical state and must be complete. A live
    Fantasy state in which an opponent board is still hidden/incomplete belongs
    to the later imperfect-information expectation solver, not this terminal
    reference kernel.
    """

    if not state.hero_is_fantasy or state.round_index != -1:
        raise ValueError("exact Fantasy solver requires Hero Fantasy round_index=-1")
    incoming = tuple(state.hero_incoming)
    if len(incoming) not in range(14, 18):
        raise ValueError("exact Fantasy solver requires 14..17 Hero incoming cards")
    if state.player(state.hero_chair).board.filled_count() != 0:
        raise ValueError("Fantasy terminal solver requires an empty committed Hero board")

    opponent_boards = tuple(
        player.board for player in state.players if player.chair != state.hero_chair
    )
    if not opponent_boards or not all(board.is_complete() for board in opponent_boards):
        raise ValueError("all opponent boards must be complete for exact Fantasy terminal scoring")
    opponents = tuple(
        _resolve_opponent(board, equality_allowed=equality_allowed)
        for board in opponent_boards
    )

    n = len(incoming)
    indices = tuple(range(n))

    top_candidates_by_mask: dict[int, tuple[HandRank, ...]] = {}
    for combo in combinations(indices, 3):
        mask = _mask(combo)
        cards = tuple(incoming[i] for i in combo)
        top_candidates_by_mask[mask] = _top_rank_candidates_cached(
            _canonical_eval_key(cards, 3)
        )

    five_candidates_by_mask: dict[int, tuple[HandRank, ...]] = {}
    for combo in combinations(indices, 5):
        mask = _mask(combo)
        cards = tuple(incoming[i] for i in combo)
        five_candidates_by_mask[mask] = _five_rank_candidates_cached(
            _canonical_eval_key(cards, 5)
        )

    best_value: float | None = None
    best_current = 0
    best_refantasy = False
    best_continuation = 0.0
    best_ranks: tuple[HandRank, HandRank, HandRank] | None = None
    best_action: FantasyPlacementAction | None = None
    best_board: PlayerBoard | None = None
    tied_best_count = 0

    bottom_middle_pairs = 0
    middle_order_pruned = 0
    top_partitions_tested = 0
    top_order_pruned = 0
    valid_boards_scored = 0

    for bottom_indices in combinations(indices, 5):
        bottom_mask = _mask(bottom_indices)
        bottom_candidates = five_candidates_by_mask[bottom_mask]
        after_bottom = tuple(i for i in indices if not (bottom_mask & (1 << i)))

        for middle_indices in combinations(after_bottom, 5):
            bottom_middle_pairs += 1
            middle_mask = _mask(middle_indices)
            middle_candidates = five_candidates_by_mask[middle_mask]
            bottom = bottom_candidates[0]
            middle = next(
                (
                    candidate
                    for candidate in middle_candidates
                    if _rank_is_not_stronger_than(
                        candidate, bottom, equality_allowed=equality_allowed
                    )
                ),
                None,
            )
            if middle is None:
                middle_order_pruned += 1
                continue

            used_bm = bottom_mask | middle_mask
            after_middle = tuple(i for i in indices if not (used_bm & (1 << i)))
            for top_indices in combinations(after_middle, 3):
                top_partitions_tested += 1
                top_mask = _mask(top_indices)
                top_candidates = top_candidates_by_mask[top_mask]
                ranks = _resolve_cached_candidates(
                    top_candidates,
                    middle_candidates,
                    bottom_candidates,
                    equality_allowed=equality_allowed,
                )
                if ranks is None:
                    top_order_pruned += 1
                    continue

                valid_boards_scored += 1
                current = _score_valid_hero_ranks(ranks, opponents)
                qualifies = _refantasy_from_resolved_ranks(ranks)
                continuation = (
                    float(refantasy_continuation_value) if qualifies else 0.0
                )
                total = float(current) + continuation

                if best_value is None or total > best_value + 1e-12:
                    action, board = _action_from_masks(
                        incoming,
                        top_mask=top_mask,
                        middle_mask=middle_mask,
                        bottom_mask=bottom_mask,
                    )
                    best_value = total
                    best_current = current
                    best_refantasy = qualifies
                    best_continuation = continuation
                    best_ranks = ranks
                    best_action = action
                    best_board = board
                    tied_best_count = 1
                elif abs(total - best_value) <= 1e-12:
                    tied_best_count += 1
                    action, board = _action_from_masks(
                        incoming,
                        top_mask=top_mask,
                        middle_mask=middle_mask,
                        bottom_mask=bottom_mask,
                    )
                    # Stable canonical tie-break. It does not change EV and makes
                    # regression output deterministic across Python versions.
                    assert best_action is not None
                    if action.key() < best_action.key():
                        best_current = current
                        best_refantasy = qualifies
                        best_continuation = continuation
                        best_ranks = ranks
                        best_action = action
                        best_board = board

    if best_value is None or best_action is None or best_board is None or best_ranks is None:
        raise RuntimeError("no non-fouled Fantasy board exists for this incoming set")

    stats = FantasySearchStats(
        incoming_cards=n,
        top_subsets=len(top_candidates_by_mask),
        five_subsets=len(five_candidates_by_mask),
        bottom_middle_pairs=bottom_middle_pairs,
        middle_order_pruned=middle_order_pruned,
        top_partitions_tested=top_partitions_tested,
        top_order_pruned=top_order_pruned,
        valid_boards_scored=valid_boards_scored,
    )
    return FantasyDecision(
        action=best_action,
        board=best_board,
        resolved_ranks=best_ranks,
        current_hand_points=best_current,
        refantasy_qualifies=best_refantasy,
        continuation_points=best_continuation,
        total_value=best_value,
        tied_best_count=tied_best_count,
        stats=stats,
    )
