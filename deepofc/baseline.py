from __future__ import annotations

"""Deterministic quality-aware policy for the FP0 simulator milestone.

This module is intentionally *not* the final DeepOFC strategy.  Its job is to
close the runtime loop before the long Ryzen-9 External Sampling training run is
ready, while avoiding obviously bad/random placements.

Design constraints:
- every returned action is canonical and UI-legal;
- physical JK1/JK2 identity is preserved;
- incoming visual order never affects the decision;
- exact late-street/Fantasy kernels are used whenever their information scope is
  satisfied;
- otherwise a deterministic Hero-board heuristic is used;
- Fantasy 14..17 never enumerates the 1M..171M raw action space.  A bounded
  rank-aware beam constructs a non-fouled 3/5/5 board and falls back to a wider
  deterministic feasibility search if necessary.

The policy is deliberately easy to replace: R10 consumes only the canonical
StrategyAction through ``build_runtime_turn_plan``.
"""

from dataclasses import dataclass
from itertools import combinations
from typing import Union

from .actions import FantasyPlacementAction, NormalPlacementAction, enumerate_normal_actions
from .decision import evaluate_final_normal_round
from .fantasy_solver_v2 import evaluate_fantasy_exact_subsets_v2
from .scoring import (
    HandRank,
    completed_board_ranks,
    is_foul,
    rank_five,
    rank_top,
    royalty,
)
from .simulator import (
    apply_normal_action,
    normal_fantasy_entry_cards,
    refantasy_qualifies,
)
from .state import Card, OFCState, PendingPlacement, PlayerBoard, Row


StrategyAction = Union[NormalPlacementAction, FantasyPlacementAction]

# Bounded search settings.  At 17 cards this means at most 192 selected Bottom
# candidates, 792 Middle subsets per Bottom and 32 retained Middles before the
# tiny <=35 Top-subset search.  All row ranks are cached locally by card subset.
_FANTASY_BOTTOM_BEAM = 192
_FANTASY_MIDDLE_BEAM = 32


@dataclass(frozen=True)
class BaselineDecision:
    action: StrategyAction
    source: str
    score: float


def _opponent_boards(state: OFCState) -> tuple[PlayerBoard, ...]:
    return tuple(
        player.board for player in state.players if player.chair != state.hero_chair
    )


def _all_opponents_complete(state: OFCState) -> bool:
    opponents = _opponent_boards(state)
    return bool(opponents) and all(board.is_complete() for board in opponents)


def _rank_scalar(rank: HandRank) -> float:
    """Map HandRank lexicographic order to a deterministic monotone scalar."""

    # A category step dominates every possible tiebreak contribution.
    value = float(int(rank.category) * 1_000_000)
    weights = (50_625, 3_375, 225, 15, 1)  # 15^4 .. 15^0
    for item, weight in zip(rank.tiebreak, weights):
        value += float(item * weight)
    return value / 1_000_000.0


def _row_complete_utility(cards: tuple[Card, ...], row: Row) -> float:
    rank = rank_top(cards) if row == Row.TOP else rank_five(cards)
    return 0.70 * _rank_scalar(rank) + float(royalty(row, rank))


def _partial_row_utility(cards: tuple[Card, ...], row: Row) -> float:
    """Cheap structural potential for an incomplete row.

    This is not an EV model.  It rewards duplicate structure, suit/straight
    connectivity and high cards, with extra value for Joker flexibility.  A
    complete row immediately switches to the exact rank/royalty evaluator.
    """

    capacity = 3 if row == Row.TOP else 5
    if len(cards) == capacity:
        return _row_complete_utility(cards, row)

    standards = tuple(card for card in cards if not card.is_joker)
    jokers = len(cards) - len(standards)
    ranks = [int(card.rank) for card in standards if card.rank is not None]
    counts: dict[int, int] = {}
    for rank in ranks:
        counts[rank] = counts.get(rank, 0) + 1
    duplicate_pairs = sum(count * (count - 1) / 2.0 for count in counts.values())
    high_card_mass = sum(ranks) / 14.0

    if row == Row.TOP:
        # Top earns most of its strategic value from pairs/trips and high ranks.
        return 2.8 * duplicate_pairs + 0.28 * high_card_mass + 3.2 * jokers

    suit_counts: dict[str, int] = {}
    for card in standards:
        assert card.suit is not None
        suit_counts[card.suit] = suit_counts.get(card.suit, 0) + 1
    max_suit = max(suit_counts.values(), default=0)

    rank_set = set(ranks)
    # Best occupancy of a five-rank straight window; wheel handled explicitly.
    straight_windows = [set((14, 2, 3, 4, 5))]
    straight_windows.extend(set(range(start, start + 5)) for start in range(2, 11))
    connectivity = max((len(rank_set & window) for window in straight_windows), default=0)

    value = (
        1.45 * duplicate_pairs
        + 0.36 * max_suit
        + 0.42 * connectivity
        + 0.10 * high_card_mass
        + 3.0 * jokers
    )
    # Middle royalties are richer than Bottom royalties, so equal structural
    # potential is slightly more useful there.
    if row == Row.MIDDLE:
        value *= 1.08
    return value


def _irreversible_complete_row_violation(board: PlayerBoard) -> bool:
    """Catch a foul that future cards can no longer repair.

    We only compare completed non-Joker rows here.  Complete-board Joker ordering
    is handled by the exact board-aware evaluator; using independent wildcard
    maxima on a partial board could falsely reject a repairable state.
    """

    if board.is_complete():
        return is_foul(board, equality_allowed=True)

    if (
        len(board.middle) == 5
        and len(board.bottom) == 5
        and not any(card.is_joker for card in (*board.middle, *board.bottom))
        and rank_five(board.bottom) < rank_five(board.middle)
    ):
        return True
    if (
        len(board.top) == 3
        and len(board.middle) == 5
        and not any(card.is_joker for card in (*board.top, *board.middle))
        and rank_five(board.middle) < rank_top(board.top)
    ):
        return True
    return False


def _completed_board_utility(
    board: PlayerBoard,
    *,
    normal_mode: bool,
    equality_allowed: bool,
) -> float:
    if is_foul(board, equality_allowed=equality_allowed):
        return -1_000_000.0

    top, middle, bottom = completed_board_ranks(
        board, equality_allowed=equality_allowed
    )
    royalties = (
        royalty(Row.TOP, top)
        + royalty(Row.MIDDLE, middle)
        + royalty(Row.BOTTOM, bottom)
    )
    # Strength is a secondary term behind actual OFC royalty points.
    strength = (
        0.55 * _rank_scalar(top)
        + 0.70 * _rank_scalar(middle)
        + 0.70 * _rank_scalar(bottom)
    )
    bonus = 0.0
    if normal_mode:
        fantasy_cards = normal_fantasy_entry_cards(
            board, equality_allowed=equality_allowed
        )
        bonus = {None: 0.0, 14: 5.0, 15: 6.0, 16: 7.5, 17: 10.0}[fantasy_cards]
    elif refantasy_qualifies(board, equality_allowed=equality_allowed):
        bonus = 7.0
    return float(royalties) + strength + bonus


def _partial_board_utility(board: PlayerBoard, *, equality_allowed: bool) -> float:
    if _irreversible_complete_row_violation(board):
        return -1_000_000.0
    if board.is_complete():
        return _completed_board_utility(
            board,
            normal_mode=True,
            equality_allowed=equality_allowed,
        )

    return (
        _partial_row_utility(board.top, Row.TOP)
        + _partial_row_utility(board.middle, Row.MIDDLE)
        + _partial_row_utility(board.bottom, Row.BOTTOM)
    )


def _choose_normal_heuristic(
    state: OFCState,
    *,
    equality_allowed: bool,
) -> BaselineDecision:
    hero_board = state.player(state.hero_chair).board
    candidates: list[tuple[float, tuple, NormalPlacementAction]] = []
    for action in enumerate_normal_actions(state):
        board_after, _ = apply_normal_action(
            hero_board,
            action,
            round_index=state.round_index,
            incoming=state.hero_incoming,
        )
        score = _partial_board_utility(
            board_after, equality_allowed=equality_allowed
        )
        candidates.append((score, action.key(), action))

    if not candidates:
        raise RuntimeError("baseline normal policy found no legal action")
    best_score = max(item[0] for item in candidates)
    tied = [item for item in candidates if abs(item[0] - best_score) <= 1e-12]
    _, _, action = min(tied, key=lambda item: item[1])
    return BaselineDecision(action, "normal_quality_heuristic_v1", best_score)


def _make_fantasy_action(
    incoming: tuple[Card, ...],
    *,
    top: tuple[Card, ...],
    middle: tuple[Card, ...],
    bottom: tuple[Card, ...],
) -> FantasyPlacementAction:
    kept = set((*top, *middle, *bottom))
    discards = tuple(card for card in incoming if card not in kept)
    return FantasyPlacementAction(
        placements=(
            *(PendingPlacement(card, Row.TOP) for card in top),
            *(PendingPlacement(card, Row.MIDDLE) for card in middle),
            *(PendingPlacement(card, Row.BOTTOM) for card in bottom),
        ),
        discards=discards,
    )


def _choose_fantasy_heuristic(
    state: OFCState,
    *,
    equality_allowed: bool,
) -> BaselineDecision:
    # Canonicalize the physical input first: visual fan/reflow order must not
    # change the strategic choice.
    incoming = tuple(sorted(state.hero_incoming, key=lambda card: card.code))
    n = len(incoming)
    if n not in range(14, 18):
        raise ValueError("Fantasy baseline requires 14..17 incoming cards")

    five_cache: dict[tuple[Card, ...], HandRank] = {}
    five_utility: dict[tuple[Card, ...], float] = {}
    for subset in combinations(incoming, 5):
        key = tuple(sorted(subset, key=lambda card: card.code))
        rank = rank_five(key)
        five_cache[key] = rank
        # Generic 5-card strength for beam ordering.  Row-specific royalty is
        # added when the subset is considered as Bottom or Middle.
        five_utility[key] = _rank_scalar(rank)

    three_cache: dict[tuple[Card, ...], HandRank] = {}
    for subset in combinations(incoming, 3):
        key = tuple(sorted(subset, key=lambda card: card.code))
        three_cache[key] = rank_top(key)

    bottom_candidates = list(five_cache)
    bottom_candidates.sort(
        key=lambda cards: (
            five_utility[cards] + royalty(Row.BOTTOM, five_cache[cards]),
            tuple(card.code for card in cards),
        ),
        reverse=True,
    )

    def search(bottom_limit: int) -> BaselineDecision | None:
        best: tuple[float, tuple, FantasyPlacementAction] | None = None
        for bottom in bottom_candidates[:bottom_limit]:
            bottom_set = set(bottom)
            bottom_rank = five_cache[bottom]
            remaining_after_bottom = tuple(
                card for card in incoming if card not in bottom_set
            )

            middle_candidates: list[tuple[float, tuple[Card, ...], HandRank]] = []
            for middle_raw in combinations(remaining_after_bottom, 5):
                middle = tuple(sorted(middle_raw, key=lambda card: card.code))
                middle_rank = five_cache[middle]
                if middle_rank > bottom_rank:
                    continue
                middle_score = (
                    five_utility[middle]
                    + royalty(Row.MIDDLE, middle_rank)
                )
                middle_candidates.append((middle_score, middle, middle_rank))
            middle_candidates.sort(
                key=lambda item: (item[0], tuple(card.code for card in item[1])),
                reverse=True,
            )

            # The normal beam is bounded.  The wider fallback passes a larger
            # bottom_limit but keeps this cap; if no board is found, the final
            # deterministic feasibility fallback below removes it entirely.
            for _, middle, middle_rank in middle_candidates[:_FANTASY_MIDDLE_BEAM]:
                used = bottom_set | set(middle)
                remaining_for_top = tuple(card for card in incoming if card not in used)
                for top_raw in combinations(remaining_for_top, 3):
                    top = tuple(sorted(top_raw, key=lambda card: card.code))
                    top_rank = three_cache[top]
                    if top_rank > middle_rank:
                        continue
                    action = _make_fantasy_action(
                        incoming,
                        top=top,
                        middle=middle,
                        bottom=bottom,
                    )
                    board = PlayerBoard(top=top, middle=middle, bottom=bottom)
                    if is_foul(board, equality_allowed=equality_allowed):
                        continue
                    score = _completed_board_utility(
                        board,
                        normal_mode=False,
                        equality_allowed=equality_allowed,
                    )
                    item = (score, action.key(), action)
                    if best is None or score > best[0] + 1e-12 or (
                        abs(score - best[0]) <= 1e-12 and action.key() < best[1]
                    ):
                        best = item
        if best is None:
            return None
        return BaselineDecision(best[2], "fantasy_quality_beam_v1", best[0])

    decision = search(min(_FANTASY_BOTTOM_BEAM, len(bottom_candidates)))
    if decision is not None:
        return decision

    # Extremely defensive fallback: widen Bottom search, and for each Bottom use
    # every legal Middle until the first non-fouled Top exists.  This path is not
    # expected on ordinary 14..17-card deals but guarantees the baseline does not
    # turn a rare geometry/card mix into a silent no-action state.
    for bottom in bottom_candidates:
        bottom_set = set(bottom)
        bottom_rank = five_cache[bottom]
        remaining_after_bottom = tuple(card for card in incoming if card not in bottom_set)
        middle_candidates = []
        for middle_raw in combinations(remaining_after_bottom, 5):
            middle = tuple(sorted(middle_raw, key=lambda card: card.code))
            middle_rank = five_cache[middle]
            if middle_rank <= bottom_rank:
                middle_candidates.append((middle, middle_rank))
        middle_candidates.sort(
            key=lambda item: (
                five_utility[item[0]] + royalty(Row.MIDDLE, item[1]),
                tuple(card.code for card in item[0]),
            ),
            reverse=True,
        )
        for middle, middle_rank in middle_candidates:
            used = bottom_set | set(middle)
            remaining_for_top = tuple(card for card in incoming if card not in used)
            top_candidates = []
            for top_raw in combinations(remaining_for_top, 3):
                top = tuple(sorted(top_raw, key=lambda card: card.code))
                top_rank = three_cache[top]
                if top_rank <= middle_rank:
                    top_candidates.append((top, top_rank))
            top_candidates.sort(
                key=lambda item: (
                    _rank_scalar(item[1]) + royalty(Row.TOP, item[1]),
                    tuple(card.code for card in item[0]),
                ),
                reverse=True,
            )
            for top, _ in top_candidates:
                board = PlayerBoard(top=top, middle=middle, bottom=bottom)
                if is_foul(board, equality_allowed=equality_allowed):
                    continue
                action = _make_fantasy_action(
                    incoming,
                    top=top,
                    middle=middle,
                    bottom=bottom,
                )
                return BaselineDecision(
                    action,
                    "fantasy_feasibility_fallback_v1",
                    _completed_board_utility(
                        board,
                        normal_mode=False,
                        equality_allowed=equality_allowed,
                    ),
                )

    raise RuntimeError("no non-fouled Fantasy placement exists for baseline")


def choose_baseline_decision(
    state: OFCState,
    *,
    equality_allowed: bool = True,
) -> BaselineDecision:
    """Choose one deterministic legal FP0 action for the current Hero state."""

    if state.acting_chair != state.hero_chair:
        raise ValueError("baseline policy requires Hero to be the acting chair")
    if not state.hero_can_prepare:
        raise ValueError("baseline policy requires Hero placement preparation")

    if state.hero_is_fantasy:
        if _all_opponents_complete(state):
            exact = evaluate_fantasy_exact_subsets_v2(
                state,
                equality_allowed=equality_allowed,
            )
            return BaselineDecision(
                exact.decision.action,
                "fantasy_exact_v2",
                float(exact.decision.total_value),
            )
        return _choose_fantasy_heuristic(
            state,
            equality_allowed=equality_allowed,
        )

    if state.round_index == 4 and _all_opponents_complete(state):
        exact = evaluate_final_normal_round(
            state,
            _opponent_boards(state),
            equality_allowed=equality_allowed,
        )
        action_value = min(exact.best_actions, key=lambda value: value.action.key())
        return BaselineDecision(
            action_value.action,
            "normal_final_exact",
            float(action_value.total_value),
        )

    return _choose_normal_heuristic(
        state,
        equality_allowed=equality_allowed,
    )


def choose_baseline_action(
    state: OFCState,
    *,
    equality_allowed: bool = True,
) -> StrategyAction:
    """Convenience wrapper returning only the canonical strategy action."""

    return choose_baseline_decision(
        state,
        equality_allowed=equality_allowed,
    ).action
