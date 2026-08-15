from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple

from .state import Card, PlayerBoard


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
    """

    players: Tuple[RawPlayerObservation, ...]
    hero_chair: int
    dealer_chair: int
    acting_chair: int
    round_index: int
    hero_loose_cards: Tuple[Card, ...] = ()
    hero_discard_tracker: Tuple[Card, ...] = ()
    hero_can_prepare: bool = False
    hero_can_confirm: bool = False
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

    def player(self, chair: int) -> RawPlayerObservation:
        for p in self.players:
            if p.chair == chair:
                return p
        raise KeyError(chair)
