from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple


class Row(str, Enum):
    TOP = "top"
    MIDDLE = "middle"
    BOTTOM = "bottom"


ROW_CAPACITY = {
    Row.TOP: 3,
    Row.MIDDLE: 5,
    Row.BOTTOM: 5,
}

RANK_TO_VALUE = {str(n): n for n in range(2, 10)}
RANK_TO_VALUE.update({"T": 10, "J": 11, "Q": 12, "K": 13, "A": 14})
VALUE_TO_RANK = {v: k for k, v in RANK_TO_VALUE.items()}


@dataclass(frozen=True)
class Card:
    """Canonical physical card.

    Standard cards use rank 2..14 and suit c/d/h/s.
    The two physical Jokers are preserved as JK1 and JK2. Wildcard assignment
    belongs to the evaluator, not to the physical state.
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

    @property
    def code(self) -> str:
        if self.is_joker:
            return f"JK{self.joker_id}"
        assert self.rank is not None and self.suit is not None
        return f"{VALUE_TO_RANK[self.rank]}{self.suit}"

    @classmethod
    def from_code(cls, code: str) -> "Card":
        raw = str(code).strip()
        if raw in {"JK1", "JK2"}:
            return cls(joker_id=int(raw[-1]))
        if len(raw) != 2:
            raise ValueError(f"invalid card code: {code}")
        rank = RANK_TO_VALUE.get(raw[0].upper())
        suit = raw[1].lower()
        if rank is None or suit not in {"c", "d", "h", "s"}:
            raise ValueError(f"invalid card code: {code}")
        return cls(rank=rank, suit=suit)


@dataclass(frozen=True)
class PlayerBoard:
    """Canonical OFC board.

    Row order is intentionally NOT strategic slot identity. KKPoker visibly
    reorders cards within a row after confirmation (e.g. supplied frames
    000543 -> 000560). Solver state therefore stores row membership only.
    Scrapers may read visual slots, but must normalize them into these rows.
    """

    top: Tuple[Card, ...] = ()
    middle: Tuple[Card, ...] = ()
    bottom: Tuple[Card, ...] = ()

    def __post_init__(self) -> None:
        for row in Row:
            cards = self.row(row)
            if len(cards) > ROW_CAPACITY[row]:
                raise ValueError(f"{row.value} row exceeds capacity {ROW_CAPACITY[row]}")
        cards = self.cards()
        if len(cards) != len(set(cards)):
            raise ValueError("duplicate physical card inside board")

    def row(self, row: Row) -> tuple[Card, ...]:
        if row == Row.TOP:
            return self.top
        if row == Row.MIDDLE:
            return self.middle
        return self.bottom

    def cards(self) -> tuple[Card, ...]:
        return (*self.top, *self.middle, *self.bottom)

    def filled_count(self) -> int:
        return len(self.cards())

    def is_complete(self) -> bool:
        return (
            len(self.top) == ROW_CAPACITY[Row.TOP]
            and len(self.middle) == ROW_CAPACITY[Row.MIDDLE]
            and len(self.bottom) == ROW_CAPACITY[Row.BOTTOM]
        )


@dataclass(frozen=True)
class PlayerState:
    chair: int
    board: PlayerBoard = field(default_factory=PlayerBoard)
    name: str = ""
    fantasy: bool = False
    sitting_out: bool = False
    hidden_discard_count: int = 0
    hidden_incoming_count: int = 0

    def __post_init__(self) -> None:
        if self.hidden_discard_count < 0:
            raise ValueError("hidden_discard_count must be non-negative")
        if self.hidden_incoming_count < 0:
            raise ValueError("hidden_incoming_count must be non-negative")
        if self.fantasy:
            if self.hidden_incoming_count not in (0, 14, 15, 16, 17):
                raise ValueError("Fantasy hidden incoming count must be 0 or 14..17")
        elif self.hidden_incoming_count not in (0, 3, 5):
            raise ValueError("normal-play hidden incoming count must be 0, 3 or 5")


@dataclass(frozen=True)
class PendingPlacement:
    """Tentative hero placement visible in the client before Confirm.

    KKPoker auto-sorts cards inside a row after confirmation, so a pending
    action chooses only a destination row, not a persistent slot.
    """

    card: Card
    row: Row


@dataclass(frozen=True)
class OFCState:
    """Canonical observation/decision state shared by solver, replay and OH.

    The target runtime variant is one concrete product: KKPoker OFC Joker
    Ultimate. Fantasy is a state of that variant, not a separate `mode`.

    In normal Pineapple play, `round_index` is 0..4 and `hero_incoming` contains
    the current 5-card first deal or 3-card later deal, including cards already
    dragged tentatively to a row but not yet confirmed.

    When Hero is in Fantasy (`player(hero_chair).fantasy == True`),
    `round_index == -1` deliberately separates the one-shot Fantasy placement
    from the normal five-round sequence. Hero may receive 14..17 physical cards
    and builds the complete 13-card 3/5/5 board at once; unused cards are the
    Hero-known Fantasy discards.

    `hero_pending` records tentative card->row assignments. This distinction is
    necessary because KKPoker allows pre-arrangement before Confirm and visibly
    re-sorts cards inside rows. Only `hero_can_confirm` marks a state that can be
    committed.

    Opponent discarded-card identities and current incoming-card identities
    remain hidden unless separately proven observable. Counts may be retained
    without inventing identities or row destinations.
    """

    players: Tuple[PlayerState, ...]
    hero_chair: int
    dealer_chair: int
    acting_chair: int
    round_index: int  # 0..4 normal; -1 when Hero is in one-shot Fantasy
    hero_incoming: Tuple[Card, ...] = ()
    hero_discards: Tuple[Card, ...] = ()
    hero_pending: Tuple[PendingPlacement, ...] = ()
    hero_can_prepare: bool = False
    hero_can_confirm: bool = False
    action_required: bool = False
    mode: str = "joker_ultimate"

    def __post_init__(self) -> None:
        if self.mode != "joker_ultimate":
            raise ValueError("DeepOFC canonical runtime mode must be joker_ultimate")
        # Five cards on street 1 plus four later 3-card draws require 17 dealt
        # cards per normal player. Together with the 54-card physical deck and
        # supplied evidence, the supported KKPoker client scope is 2-3 players.
        if len(self.players) not in (2, 3):
            raise ValueError("KKPoker Pineapple/Joker state must contain 2 or 3 players")
        chairs = [p.chair for p in self.players]
        if len(chairs) != len(set(chairs)):
            raise ValueError("duplicate player chairs")
        if self.hero_chair not in chairs:
            raise ValueError("hero_chair not present")
        if self.dealer_chair not in chairs:
            raise ValueError("dealer_chair not present")
        if self.acting_chair not in chairs:
            raise ValueError("acting_chair not present")

        if self.hero_is_fantasy:
            if self.round_index != -1:
                raise ValueError("Hero Fantasy state requires round_index=-1")
            if self.hero_incoming and len(self.hero_incoming) not in range(14, 18):
                raise ValueError("Hero Fantasy incoming count must be 14..17")
            if self.action_required and len(self.hero_incoming) not in range(14, 18):
                raise ValueError("Fantasy action requires 14..17 Hero incoming cards")
        elif self.round_index not in range(5):
            raise ValueError("normal round_index must be 0..4")

        if self.action_required and not self.hero_can_confirm:
            raise ValueError("action_required implies hero_can_confirm")
        if self.hero_can_confirm and self.acting_chair != self.hero_chair:
            raise ValueError("hero_can_confirm requires Hero to be acting chair")
        self.validate_physical_cards()
        self.validate_pending()

    @property
    def hero_is_fantasy(self) -> bool:
        return self.player(self.hero_chair).fantasy

    def player(self, chair: int) -> PlayerState:
        for p in self.players:
            if p.chair == chair:
                return p
        raise KeyError(chair)

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

    def validate_pending(self) -> None:
        incoming = set(self.hero_incoming)
        seen_cards: set[Card] = set()
        additions = {row: 0 for row in Row}
        for placement in self.hero_pending:
            if placement.card not in incoming:
                raise ValueError("pending placement card must belong to hero_incoming")
            if placement.card in seen_cards:
                raise ValueError("same incoming card cannot be pending twice")
            seen_cards.add(placement.card)
            additions[placement.row] += 1

        board = self.player(self.hero_chair).board
        for row in Row:
            if len(board.row(row)) + additions[row] > ROW_CAPACITY[row]:
                raise ValueError(f"pending placements overflow {row.value} row")

    def unassigned_incoming(self) -> tuple[Card, ...]:
        assigned = {p.card for p in self.hero_pending}
        return tuple(c for c in self.hero_incoming if c not in assigned)

    def confirm_shape_is_legal(self) -> bool:
        board = self.player(self.hero_chair).board
        if self.hero_is_fantasy:
            if len(self.hero_incoming) not in range(14, 18):
                return False
            # Fantasy is a one-shot full-board placement. Any current visual
            # pre-arrangement is represented by hero_pending; committed board
            # cards, if present during reconstruction, reduce remaining slots.
            if board.filled_count() + len(self.hero_pending) != 13:
                return False
            return len(self.unassigned_incoming()) == len(self.hero_incoming) - len(self.hero_pending)

        required = 5 if self.round_index == 0 else 2
        if len(self.hero_pending) != required:
            return False
        if self.round_index == 0:
            return len(self.hero_incoming) == 5 and len(self.unassigned_incoming()) == 0
        return len(self.hero_incoming) == 3 and len(self.unassigned_incoming()) == 1
