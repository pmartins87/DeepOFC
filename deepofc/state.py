from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple


class Row(str, Enum):
    TOP = "top"
    MIDDLE = "middle"
    BOTTOM = "bottom"


@dataclass(frozen=True, order=True)
class Card:
    """Canonical physical card.

    rank is one of 2..14 for standard cards. joker_id is 1 or 2 for physical
    jokers and rank/suit are None. We keep physical Joker identity even if game
    evaluation later assigns it a wildcard representation.
    """

    rank: Optional[int] = None
    suit: Optional[str] = None
    joker_id: Optional[int] = None

    def __post_init__(self) -> None:
        if self.joker_id is not None:
            if self.joker_id not in (1, 2):
                raise ValueError("joker_id must be 1 or 2")
            if self.rank is not None or self.suit is not None:
                raise ValueError("physical Joker cannot also have rank/suit")
            return
        if self.rank not in range(2, 15):
            raise ValueError("standard card rank must be 2..14")
        if self.suit not in {"c", "d", "h", "s"}:
            raise ValueError("standard card suit must be c/d/h/s")

    @property
    def is_joker(self) -> bool:
        return self.joker_id is not None


@dataclass(frozen=True)
class PlayerBoard:
    top: Tuple[Optional[Card], Optional[Card], Optional[Card]] = (None,) * 3
    middle: Tuple[Optional[Card], Optional[Card], Optional[Card], Optional[Card], Optional[Card]] = (None,) * 5
    bottom: Tuple[Optional[Card], Optional[Card], Optional[Card], Optional[Card], Optional[Card]] = (None,) * 5

    def cards(self) -> tuple[Card, ...]:
        return tuple(c for c in (*self.top, *self.middle, *self.bottom) if c is not None)

    def filled_count(self) -> int:
        return len(self.cards())

    def is_complete(self) -> bool:
        return self.filled_count() == 13


@dataclass(frozen=True)
class PlayerState:
    chair: int
    board: PlayerBoard = field(default_factory=PlayerBoard)
    name: str = ""
    fantasy: bool = False
    sitting_out: bool = False


@dataclass(frozen=True)
class OFCState:
    """Canonical decision state shared by solver, replay validation and OH bridge.

    `hero_incoming` contains cards dealt to Hero for the current placement action
    that have not yet been committed to the board. `hero_discards` are private
    dead cards known to Hero. Opponent discarded cards must not be added unless
    they are actually observable from the KKPoker client at decision time.
    """

    players: Tuple[PlayerState, ...]
    hero_chair: int
    dealer_chair: int
    acting_chair: int
    round_index: int  # 0..4 for the five normal OFC rounds
    hero_incoming: Tuple[Card, ...] = ()
    hero_discards: Tuple[Card, ...] = ()
    action_required: bool = False
    mode: str = "joker"

    def __post_init__(self) -> None:
        if not self.players:
            raise ValueError("state must contain players")
        chairs = [p.chair for p in self.players]
        if len(chairs) != len(set(chairs)):
            raise ValueError("duplicate player chairs")
        if self.hero_chair not in chairs:
            raise ValueError("hero_chair not present")
        if self.dealer_chair not in chairs:
            raise ValueError("dealer_chair not present")
        if self.acting_chair not in chairs:
            raise ValueError("acting_chair not present")
        if self.round_index not in range(5):
            raise ValueError("round_index must be 0..4")
        self.validate_physical_cards()

    def known_cards(self) -> tuple[Card, ...]:
        cards: list[Card] = []
        for p in self.players:
            cards.extend(p.board.cards())
        cards.extend(self.hero_incoming)
        cards.extend(self.hero_discards)
        return tuple(cards)

    def validate_physical_cards(self) -> None:
        cards = self.known_cards()
        if len(cards) != len(set(cards)):
            raise ValueError("duplicate physical card in known state")
        jokers = [c for c in cards if c.is_joker]
        if len(jokers) > 2:
            raise ValueError("more than two physical Jokers in state")
