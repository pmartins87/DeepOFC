from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from itertools import combinations

from .fantasy_solver import (
    FantasyDecision,
    _action_from_masks,
    _mask,
    _rank_is_not_stronger_than,
    _refantasy_from_resolved_ranks,
    _resolve_opponent,
    _score_valid_hero_ranks,
)
from .scoring import (
    HandRank,
    _canonical_eval_key,
    _five_rank_candidates_cached,
    _top_rank_candidates_cached,
)
from .state import OFCState


@dataclass(frozen=True)
class FantasySearchStatsV2:
    incoming_cards: int
    top_subsets: int
    five_subsets: int
    bottom_middle_pairs: int
    middle_order_pruned: int
    top_frontiers_built: int
    top_rank_queries: int
    top_rank_query_pruned: int
    valid_boards_scored: int


@dataclass(frozen=True)
class FantasyDecisionV2:
    """Exact optimized Fantasy terminal decision for non-negative continuation."""

    decision: FantasyDecision
    stats_v2: FantasySearchStatsV2


@dataclass
class _TopFrontier:
    """All achievable Top ranks for one leftover physical-card mask.

    `masks_by_rank` keeps the physical 3-card subsets that can attain each rank.
    When we query the globally strongest achievable rank below Middle, any mask
    containing that rank necessarily resolves to it under the frozen Joker rule:
    if it had a stronger eligible candidate, that stronger rank would also be in
    this frontier and would have been selected instead.
    """

    ranks: tuple[HandRank, ...]
    masks_by_rank: dict[HandRank, tuple[int, ...]]


def _strongest_middle(
    candidates: tuple[HandRank, ...],
    bottom: HandRank,
    *,
    equality_allowed: bool,
) -> HandRank | None:
    return next(
        (
            candidate
            for candidate in candidates
            if _rank_is_not_stronger_than(
                candidate, bottom, equality_allowed=equality_allowed
            )
        ),
        None,
    )


def _query_top_frontier(
    frontier: _TopFrontier,
    middle: HandRank,
    *,
    equality_allowed: bool,
) -> tuple[HandRank, tuple[int, ...]] | None:
    ranks = frontier.ranks
    if equality_allowed:
        index = bisect_right(ranks, middle) - 1
    else:
        index = bisect_left(ranks, middle) - 1
    if index < 0:
        return None
    rank = ranks[index]
    return rank, frontier.masks_by_rank[rank]


def evaluate_fantasy_exact_subsets_v2(
    state: OFCState,
    *,
    refantasy_continuation_value: float = 0.0,
    equality_allowed: bool = True,
) -> FantasyDecisionV2:
    """Exact Fantasy solver that collapses repeated Top enumeration.

    V1 tests every Top physical subset after every Bottom/Middle split. V2 notes
    that with a non-negative re-Fantasy continuation, a stronger legal resolved
    Top rank can never reduce terminal utility: row result, Top royalty, scoop
    status and re-Fantasy qualification are all monotone non-decreasing in Top
    rank. Therefore for each leftover-card mask V2 builds one exact frontier of
    achievable Top ranks and queries only the strongest rank <= Middle.

    This removes the C(N-10, 3) inner loop without approximating the optimum.
    Negative continuation values are deliberately rejected; V1 remains the
    general semantic reference until/unless that artificial case is needed.
    """

    if refantasy_continuation_value < 0:
        raise ValueError("Fantasy V2 requires non-negative re-Fantasy continuation value")
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
    all_mask = (1 << n) - 1

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

    frontier_cache: dict[int, _TopFrontier] = {}

    def frontier_for(remaining_mask: int) -> _TopFrontier:
        cached = frontier_cache.get(remaining_mask)
        if cached is not None:
            return cached
        remaining_indices = tuple(i for i in indices if remaining_mask & (1 << i))
        by_rank: dict[HandRank, list[int]] = {}
        for combo in combinations(remaining_indices, 3):
            top_mask = _mask(combo)
            for rank in top_candidates_by_mask[top_mask]:
                by_rank.setdefault(rank, []).append(top_mask)
        frozen = _TopFrontier(
            ranks=tuple(sorted(by_rank)),
            masks_by_rank={rank: tuple(sorted(set(masks))) for rank, masks in by_rank.items()},
        )
        frontier_cache[remaining_mask] = frozen
        return frozen

    best_value: float | None = None
    best_current = 0
    best_refantasy = False
    best_continuation = 0.0
    best_ranks = None
    best_action = None
    best_board = None
    representative_ties = 0

    bottom_middle_pairs = 0
    middle_order_pruned = 0
    top_rank_queries = 0
    top_rank_query_pruned = 0
    valid_boards_scored = 0

    for bottom_indices in combinations(indices, 5):
        bottom_mask = _mask(bottom_indices)
        bottom_candidates = five_candidates_by_mask[bottom_mask]
        bottom = bottom_candidates[0]
        after_bottom = tuple(i for i in indices if not (bottom_mask & (1 << i)))

        for middle_indices in combinations(after_bottom, 5):
            bottom_middle_pairs += 1
            middle_mask = _mask(middle_indices)
            middle_candidates = five_candidates_by_mask[middle_mask]
            middle = _strongest_middle(
                middle_candidates,
                bottom,
                equality_allowed=equality_allowed,
            )
            if middle is None:
                middle_order_pruned += 1
                continue

            remaining_mask = all_mask ^ (bottom_mask | middle_mask)
            top_rank_queries += 1
            top_result = _query_top_frontier(
                frontier_for(remaining_mask),
                middle,
                equality_allowed=equality_allowed,
            )
            if top_result is None:
                top_rank_query_pruned += 1
                continue
            top, candidate_top_masks = top_result
            ranks = (top, middle, bottom)
            valid_boards_scored += 1

            current = _score_valid_hero_ranks(ranks, opponents)
            qualifies = _refantasy_from_resolved_ranks(ranks)
            continuation = (
                float(refantasy_continuation_value) if qualifies else 0.0
            )
            total = float(current) + continuation

            if best_value is not None and total < best_value - 1e-12:
                continue

            # Only materialize physical actions when this Bottom/Middle pair can
            # establish or tie the incumbent. Among Top masks with the same
            # resolved rank, choose the canonical smallest action key.
            pair_action = None
            pair_board = None
            for top_mask in candidate_top_masks:
                action, board = _action_from_masks(
                    incoming,
                    top_mask=top_mask,
                    middle_mask=middle_mask,
                    bottom_mask=bottom_mask,
                )
                if pair_action is None or action.key() < pair_action.key():
                    pair_action = action
                    pair_board = board
            assert pair_action is not None and pair_board is not None

            if best_value is None or total > best_value + 1e-12:
                best_value = total
                best_current = current
                best_refantasy = qualifies
                best_continuation = continuation
                best_ranks = ranks
                best_action = pair_action
                best_board = pair_board
                representative_ties = 1
            else:
                representative_ties += 1
                assert best_action is not None
                if pair_action.key() < best_action.key():
                    best_current = current
                    best_refantasy = qualifies
                    best_continuation = continuation
                    best_ranks = ranks
                    best_action = pair_action
                    best_board = pair_board

    if best_value is None or best_action is None or best_board is None or best_ranks is None:
        raise RuntimeError("no non-fouled Fantasy board exists for this incoming set")

    # Reuse the stable public decision shape. V2 tie count is explicitly the
    # number of best Bottom/Middle representatives, not all physical Top boards.
    from .fantasy_solver import FantasySearchStats

    compatibility_stats = FantasySearchStats(
        incoming_cards=n,
        top_subsets=len(top_candidates_by_mask),
        five_subsets=len(five_candidates_by_mask),
        bottom_middle_pairs=bottom_middle_pairs,
        middle_order_pruned=middle_order_pruned,
        top_partitions_tested=top_rank_queries,
        top_order_pruned=top_rank_query_pruned,
        valid_boards_scored=valid_boards_scored,
    )
    decision = FantasyDecision(
        action=best_action,
        board=best_board,
        resolved_ranks=best_ranks,
        current_hand_points=best_current,
        refantasy_qualifies=best_refantasy,
        continuation_points=best_continuation,
        total_value=best_value,
        tied_best_count=representative_ties,
        stats=compatibility_stats,
    )
    return FantasyDecisionV2(
        decision=decision,
        stats_v2=FantasySearchStatsV2(
            incoming_cards=n,
            top_subsets=len(top_candidates_by_mask),
            five_subsets=len(five_candidates_by_mask),
            bottom_middle_pairs=bottom_middle_pairs,
            middle_order_pruned=middle_order_pruned,
            top_frontiers_built=len(frontier_cache),
            top_rank_queries=top_rank_queries,
            top_rank_query_pruned=top_rank_query_pruned,
            valid_boards_scored=valid_boards_scored,
        ),
    )
