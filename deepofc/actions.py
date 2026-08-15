from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, product
from math import comb
from typing import Iterable, Iterator

from .state import Card, OFCState, PendingPlacement, ROW_CAPACITY, Row


@dataclass(frozen=True)
class NormalPlacementAction:
    """Canonical normal-round OFC action.

    Row placement is strategic; left-to-right visual slot order is not. Round 0
    has no discard. Rounds 1–4 discard exactly one of the three incoming cards.
    """

    placements: tuple[PendingPlacement, ...]
    discard: Card | None = None

    def __post_init__(self) -> None:
        cards = [p.card for p in self.placements]
        if len(cards) != len(set(cards)):
            raise ValueError("same card placed more than once")
        if self.discard is not None and self.discard in cards:
            raise ValueError("discarded card cannot also be placed")

    @property
    def placed_cards(self) -> frozenset[Card]:
        return frozenset(p.card for p in self.placements)

    def key(self) -> tuple:
        return (
            tuple(sorted((p.card.code, p.row.value) for p in self.placements)),
            None if self.discard is None else self.discard.code,
        )


@dataclass(frozen=True)
class FantasyPlacementAction:
    """One complete canonical Joker Ultimate Fantasy placement.

    A Fantasy action chooses the full 3/5/5 board from 14..17 physical incoming
    cards. The remaining 1..4 cards are Hero-known discards. Visual fan order
    and left-to-right order inside a row are intentionally absent.
    """

    placements: tuple[PendingPlacement, ...]
    discards: tuple[Card, ...]

    def __post_init__(self) -> None:
        placed = tuple(p.card for p in self.placements)
        if len(placed) != 13:
            raise ValueError("Fantasy action must place exactly 13 cards")
        if len(set(placed)) != 13:
            raise ValueError("same physical card placed more than once")
        if len(self.discards) not in range(1, 5):
            raise ValueError("Fantasy action must discard 1..4 cards")
        if len(set(self.discards)) != len(self.discards):
            raise ValueError("same physical card discarded more than once")
        if set(placed) & set(self.discards):
            raise ValueError("Fantasy card cannot be both placed and discarded")
        counts = {row: 0 for row in Row}
        for placement in self.placements:
            counts[placement.row] += 1
        if counts != {Row.TOP: 3, Row.MIDDLE: 5, Row.BOTTOM: 5}:
            raise ValueError("Fantasy action must fill rows exactly 3/5/5")

    @property
    def placed_cards(self) -> frozenset[Card]:
        return frozenset(p.card for p in self.placements)

    def key(self) -> tuple:
        return (
            tuple(sorted((p.card.code, p.row.value) for p in self.placements)),
            tuple(sorted(card.code for card in self.discards)),
        )


def _row_free_slots(state: OFCState) -> dict[Row, int]:
    board = state.player(state.hero_chair).board
    return {row: ROW_CAPACITY[row] - len(board.row(row)) for row in Row}


def _placement_fits(
    free: dict[Row, int], placements: Iterable[PendingPlacement]
) -> bool:
    used = {row: 0 for row in Row}
    for p in placements:
        used[p.row] += 1
    return all(used[row] <= free[row] for row in Row)


def enumerate_normal_actions(state: OFCState) -> tuple[NormalPlacementAction, ...]:
    """Enumerate every legal normal-round card placement exactly.

    This function deliberately ignores hand strength, foul probability and Joker
    evaluation. Those determine EV, not whether a normal placement is a legal UI
    action. Fantasy is a separate action space and is not accepted here.
    """

    if state.hero_is_fantasy:
        raise ValueError("Fantasy state requires iter_fantasy_actions")
    if state.round_index not in range(5):
        raise ValueError("normal round_index must be 0..4")
    incoming = tuple(state.hero_incoming)
    expected = 5 if state.round_index == 0 else 3
    if len(incoming) != expected:
        raise ValueError(
            f"round {state.round_index} requires {expected} incoming cards, got {len(incoming)}"
        )

    free = _row_free_slots(state)
    rows = tuple(Row)
    actions: dict[tuple, NormalPlacementAction] = {}

    if state.round_index == 0:
        for destinations in product(rows, repeat=5):
            placements = tuple(
                PendingPlacement(card=card, row=row)
                for card, row in zip(incoming, destinations)
            )
            if not _placement_fits(free, placements):
                continue
            action = NormalPlacementAction(placements=placements, discard=None)
            actions[action.key()] = action
    else:
        for discard in incoming:
            placed = tuple(c for c in incoming if c != discard)
            if len(placed) != 2:
                raise ValueError("incoming physical cards must be unique")
            for destinations in product(rows, repeat=2):
                placements = tuple(
                    PendingPlacement(card=card, row=row)
                    for card, row in zip(placed, destinations)
                )
                if not _placement_fits(free, placements):
                    continue
                action = NormalPlacementAction(
                    placements=placements,
                    discard=discard,
                )
                actions[action.key()] = action

    return tuple(actions[k] for k in sorted(actions))


def _validate_fresh_fantasy_action_state(state: OFCState) -> tuple[Card, ...]:
    if not state.hero_is_fantasy:
        raise ValueError("Fantasy action generator requires Hero Fantasy state")
    if state.round_index != -1:
        raise ValueError("Fantasy action generator requires round_index=-1")
    incoming = tuple(state.hero_incoming)
    if len(incoming) not in range(14, 18):
        raise ValueError("Fantasy action requires 14..17 incoming cards")
    if len(incoming) != len(set(incoming)):
        raise ValueError("Fantasy incoming physical cards must be unique")
    if state.player(state.hero_chair).board.filled_count() != 0:
        raise ValueError("full Fantasy action generation requires an empty committed Hero board")
    return incoming


def count_fantasy_actions(state: OFCState) -> int:
    """Return the exact cardinality without materializing the huge action set.

    Even 14-card Fantasy already has 1,009,008 canonical 3/5/5 placements;
    17-card Fantasy has 171,531,360. R3 therefore exposes a lazy exact iterator
    instead of allocating the entire action space in memory.
    """

    incoming = _validate_fresh_fantasy_action_state(state)
    n = len(incoming)
    return comb(n, n - 13) * comb(13, 3) * comb(10, 5)


def iter_fantasy_actions(state: OFCState) -> Iterator[FantasyPlacementAction]:
    """Lazily enumerate every canonical full-board Fantasy action exactly once.

    Enumeration is physical-card exact but strategically canonical: row
    membership matters, fan order and within-row visual order do not. Existing
    tentative pre-arrangement is intentionally ignored because it is not yet
    committed and the strategy is choosing the complete final board.
    """

    incoming = _validate_fresh_fantasy_action_state(state)
    discard_count = len(incoming) - 13

    for discards in combinations(incoming, discard_count):
        discard_set = set(discards)
        kept = tuple(card for card in incoming if card not in discard_set)
        # Choose Top first, then Middle; Bottom is the remaining five. This is
        # a one-to-one canonical decomposition of every 3/5/5 row partition.
        for top in combinations(kept, 3):
            top_set = set(top)
            after_top = tuple(card for card in kept if card not in top_set)
            for middle in combinations(after_top, 5):
                middle_set = set(middle)
                bottom = tuple(card for card in after_top if card not in middle_set)
                placements = (
                    *(PendingPlacement(card=card, row=Row.TOP) for card in top),
                    *(PendingPlacement(card=card, row=Row.MIDDLE) for card in middle),
                    *(PendingPlacement(card=card, row=Row.BOTTOM) for card in bottom),
                )
                yield FantasyPlacementAction(
                    placements=placements,
                    discards=tuple(discards),
                )
