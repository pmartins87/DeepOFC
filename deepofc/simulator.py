from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Iterable, Sequence

from .actions import FantasyPlacementAction, NormalPlacementAction, fantasy_action_board
from .scoring import HandCategory, completed_board_ranks, is_foul, pairwise_points_standard
from .state import Card, PlayerBoard, ROW_CAPACITY, Row


def physical_deck_54() -> tuple[Card, ...]:
    """Return the canonical KKPoker Joker Ultimate physical deck.

    Physical identity is immutable: 52 standard cards plus persistent JK1/JK2.
    Joker nominal substitution belongs only to scoring, never to the deck.
    """

    return tuple(
        Card(rank=rank, suit=suit)
        for rank in range(2, 15)
        for suit in ("c", "d", "h", "s")
    ) + (Card(joker_id=1), Card(joker_id=2))


PHYSICAL_DECK_54 = physical_deck_54()


@dataclass(frozen=True)
class DeterministicDeck:
    """Immutable deterministic deck order for reproducible R4/R5 simulations."""

    cards: tuple[Card, ...]
    cursor: int = 0

    @classmethod
    def shuffled(cls, seed: int) -> "DeterministicDeck":
        cards = list(PHYSICAL_DECK_54)
        random.Random(seed).shuffle(cards)
        return cls(tuple(cards), 0)

    @classmethod
    def from_remaining(cls, remaining: Iterable[Card], *, seed: int) -> "DeterministicDeck":
        cards = list(remaining)
        if len(cards) != len(set(cards)):
            raise ValueError("remaining deck contains duplicate physical cards")
        if any(card not in PHYSICAL_DECK_54 for card in cards):
            raise ValueError("remaining deck contains non-physical card")
        random.Random(seed).shuffle(cards)
        return cls(tuple(cards), 0)

    @property
    def remaining_count(self) -> int:
        return len(self.cards) - self.cursor

    def draw(self, count: int) -> tuple[tuple[Card, ...], "DeterministicDeck"]:
        if count < 0:
            raise ValueError("draw count must be non-negative")
        end = self.cursor + count
        if end > len(self.cards):
            raise ValueError("not enough cards remaining")
        return self.cards[self.cursor:end], DeterministicDeck(self.cards, end)


def remaining_physical_cards(known: Iterable[Card]) -> tuple[Card, ...]:
    known_tuple = tuple(known)
    if len(known_tuple) != len(set(known_tuple)):
        raise ValueError("known cards contain duplicate physical cards")
    unknown = set(PHYSICAL_DECK_54) - set(known_tuple)
    if len(unknown) != 54 - len(known_tuple):
        raise ValueError("known cards contain card outside the 54-card deck")
    # Stable canonical order makes seeded simulations reproducible across runs.
    return tuple(card for card in PHYSICAL_DECK_54 if card in unknown)


def _board_with_added_cards(
    board: PlayerBoard,
    placements: Sequence[tuple[Card, Row]],
) -> PlayerBoard:
    by_row: dict[Row, list[Card]] = {
        Row.TOP: list(board.top),
        Row.MIDDLE: list(board.middle),
        Row.BOTTOM: list(board.bottom),
    }
    existing = set(board.cards())
    added: set[Card] = set()
    for card, row in placements:
        if card in existing or card in added:
            raise ValueError("same physical card cannot be added twice")
        by_row[row].append(card)
        if len(by_row[row]) > ROW_CAPACITY[row]:
            raise ValueError(f"placement overflows {row.value}")
        added.add(card)
    return PlayerBoard(
        top=tuple(by_row[Row.TOP]),
        middle=tuple(by_row[Row.MIDDLE]),
        bottom=tuple(by_row[Row.BOTTOM]),
    )


def apply_normal_action(
    board: PlayerBoard,
    action: NormalPlacementAction,
    *,
    round_index: int,
    incoming: Sequence[Card],
) -> tuple[PlayerBoard, tuple[Card, ...]]:
    """Apply one canonical normal Pineapple action exactly.

    Round 0 places all five cards and has no discard. Rounds 1..4 place two of
    three and discard exactly one. This function validates physical coverage,
    not strategy quality; a UI-legal action may still create a future/terminal
    foul.
    """

    if round_index not in range(5):
        raise ValueError("normal round_index must be 0..4")
    incoming_tuple = tuple(incoming)
    expected = 5 if round_index == 0 else 3
    if len(incoming_tuple) != expected or len(set(incoming_tuple)) != expected:
        raise ValueError(f"round {round_index} requires {expected} unique physical incoming cards")

    placed = tuple(p.card for p in action.placements)
    if round_index == 0:
        if len(placed) != 5 or action.discard is not None:
            raise ValueError("round 0 must place all five cards and discard none")
        covered = set(placed)
        discards: tuple[Card, ...] = ()
    else:
        if len(placed) != 2 or action.discard is None:
            raise ValueError("later round must place two cards and discard one")
        covered = set(placed) | {action.discard}
        discards = (action.discard,)

    if covered != set(incoming_tuple):
        raise ValueError("action must cover each incoming physical card exactly once")

    new_board = _board_with_added_cards(
        board,
        tuple((placement.card, placement.row) for placement in action.placements),
    )
    return new_board, discards


def apply_fantasy_action(action: FantasyPlacementAction) -> tuple[PlayerBoard, tuple[Card, ...]]:
    board = fantasy_action_board(action)
    if not board.is_complete():
        raise ValueError("Fantasy action did not build a complete 3/5/5 board")
    return board, tuple(action.discards)


@dataclass(frozen=True)
class RawSettlement:
    """Raw point settlement before KKPoker cash cap/rake."""

    points_by_chair: tuple[int, ...]

    @property
    def zero_sum(self) -> bool:
        return sum(self.points_by_chair) == 0


def settle_raw_points(
    boards: Sequence[PlayerBoard],
    *,
    equality_allowed: bool = True,
) -> RawSettlement:
    """Settle a complete 2- or 3-player board set by pairwise OFC scoring.

    KKPoker scoring is pairwise. Therefore 3-player raw points are the sum of
    each player's two pairwise results. Money caps/rake remain intentionally
    outside this R4 primitive until R1 freezes their exact semantics.
    """

    if len(boards) not in (2, 3):
        raise ValueError("DeepOFC currently supports 2 or 3 players")
    if not all(board.is_complete() for board in boards):
        raise ValueError("raw settlement requires complete boards")

    points = [0 for _ in boards]
    for i in range(len(boards)):
        for j in range(i + 1, len(boards)):
            score = pairwise_points_standard(
                boards[i], boards[j], equality_allowed=equality_allowed
            )
            value = score.total_points
            points[i] += value
            points[j] -= value
    result = RawSettlement(tuple(points))
    if not result.zero_sum:
        raise AssertionError("pairwise raw OFC settlement must sum to zero")
    return result


def normal_fantasy_entry_cards(
    board: PlayerBoard,
    *,
    equality_allowed: bool = True,
) -> int | None:
    """Return next-hand Fantasy card count after a normal completed board.

    Frozen Joker Ultimate progressive entry contract:
      QQ top -> 14; KK -> 15; AA -> 16; Top trips -> 17.
    A fouled board never qualifies. Pair ranks below QQ do not qualify.
    """

    if not board.is_complete():
        raise ValueError("Fantasy qualification requires complete board")
    if is_foul(board, equality_allowed=equality_allowed):
        return None
    top, _, _ = completed_board_ranks(board, equality_allowed=equality_allowed)
    if top.category == HandCategory.TRIPS:
        return 17
    if top.category != HandCategory.PAIR:
        return None
    pair_rank = top.tiebreak[0]
    return {12: 14, 13: 15, 14: 16}.get(pair_rank)


def refantasy_qualifies(
    board: PlayerBoard,
    *,
    equality_allowed: bool = True,
) -> bool:
    """Return whether a completed Fantasy board earns another Fantasy hand.

    The exact next deal count for every re-Fantasy path remains a separate rule
    problem. This predicate freezes only the already-supported qualification:
    Top trips OR Bottom quads-or-better, provided the board is not fouled.
    """

    if not board.is_complete():
        raise ValueError("re-Fantasy qualification requires complete board")
    if is_foul(board, equality_allowed=equality_allowed):
        return False
    top, _, bottom = completed_board_ranks(board, equality_allowed=equality_allowed)
    return (
        top.category == HandCategory.TRIPS
        or bottom.category >= HandCategory.QUADS
    )
