from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple

from .state import Card, PlayerBoard


NORMAL_TOTAL_DEALT_TO_ROUND = {
    5: 0,
    8: 1,
    11: 2,
    14: 3,
    17: 4,
}


def derive_normal_round_index(
    *,
    hero_visual_board_count: int,
    hero_loose_count: int,
    hero_discard_tracker_count: int,
) -> int:
    """Derive normal Pineapple round from Hero-visible physical-card accounting.

    Hero current cards may be loose or tentatively dragged over a row, so the
    split between visual-board and loose counts changes during pre-arrangement.
    Their sum plus already-known Hero discards stays invariant for the street:
    5, 8, 11, 14, 17 physical cards dealt through rounds 0..4.

    Fantasy is deliberately excluded and must use a separate observation path.
    """

    counts = (hero_visual_board_count, hero_loose_count, hero_discard_tracker_count)
    if any(v < 0 for v in counts):
        raise ValueError("visible OFC card counts must be non-negative")
    total = sum(counts)
    if total not in NORMAL_TOTAL_DEALT_TO_ROUND:
        raise ValueError(
            f"normal OFC visible-card total must be one of {sorted(NORMAL_TOTAL_DEALT_TO_ROUND)}, got {total}"
        )
    return NORMAL_TOTAL_DEALT_TO_ROUND[total]


@dataclass(frozen=True)
class RawPlayerObservation:
    """What the KKPoker frame visibly exposes for one player.

    `visual_board` is deliberately raw: for Hero it can contain tentative cards
    that were dragged over a row but not yet confirmed. For opponents, current
    undeclared cards are hidden backs and therefore appear only as a count.
    """

    chair: int
    visual_board: PlayerBoard = field(default_factory=PlayerBoard)
    hidden_incoming_count: int = 0
    hidden_discard_count: int = 0
    name: str = ""
    fantasy: bool = False
    sitting_out: bool = False

    def __post_init__(self) -> None:
        if self.hidden_incoming_count < 0:
            raise ValueError("hidden_incoming_count must be non-negative")
        if self.hidden_discard_count < 0:
            raise ValueError("hidden_discard_count must be non-negative")


@dataclass(frozen=True)
class RawOFCObservation:
    """Frame-level visual observation before strategic interpretation.

    This layer intentionally does not say which Hero row cards are committed.
    The stateful reconstructor compares it with previous confirmed state and the
    discard tracker to classify committed vs tentative cards.

    KKPoker replay evidence shows the gold Confirm button while the earlier
    opponent's timer is still active. Therefore `confirm_visible` is a raw UI
    fact and is deliberately different from canonical `hero_can_confirm`, which
    means it is strategically/legal-order safe for Hero to commit now.
    """

    players: Tuple[RawPlayerObservation, ...]
    hero_chair: int
    dealer_chair: int
    acting_chair: int
    round_index: int
    hero_loose_cards: Tuple[Card, ...] = ()
    hero_discard_tracker: Tuple[Card, ...] = ()
    hero_can_prepare: bool = False
    confirm_visible: bool = False
    mode: str = "joker_ultimate"

    def __post_init__(self) -> None:
        chairs = [p.chair for p in self.players]
        if len(self.players) not in (2, 3):
            raise ValueError("raw observation must contain 2 or 3 players")
        if len(chairs) != len(set(chairs)):
            raise ValueError("duplicate raw observation chairs")
        for chair in (self.hero_chair, self.dealer_chair, self.acting_chair):
            if chair not in chairs:
                raise ValueError("hero/dealer/actor chair missing from observation")
        if self.round_index not in range(5):
            raise ValueError("round_index must be 0..4")
        visible = []
        for p in self.players:
            visible.extend(p.visual_board.cards())
        visible.extend(self.hero_loose_cards)
        visible.extend(self.hero_discard_tracker)
        # Tentative Hero cards can be visible in a row instead of loose, but a
        # physical card must never be visible simultaneously in two places.
        if len(visible) != len(set(visible)):
            raise ValueError("duplicate physical card in raw visual observation")

        derived_round = derive_normal_round_index(
            hero_visual_board_count=self.player(self.hero_chair).visual_board.filled_count(),
            hero_loose_count=len(self.hero_loose_cards),
            hero_discard_tracker_count=len(self.hero_discard_tracker),
        )
        if derived_round != self.round_index:
            raise ValueError(
                f"round_index={self.round_index} contradicts Hero visible-card accounting round={derived_round}"
            )

    def player(self, chair: int) -> RawPlayerObservation:
        for p in self.players:
            if p.chair == chair:
                return p
        raise KeyError(chair)
