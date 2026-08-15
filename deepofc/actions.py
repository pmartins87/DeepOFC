from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Iterable

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
