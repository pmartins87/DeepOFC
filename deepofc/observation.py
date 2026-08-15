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

    Fantasy is deliberately excluded and uses `round_index=-1` plus its own
    14..17-card one-shot accounting below.
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
        if self.fantasy:
            if self.hidden_incoming_count not in (0, 14, 15, 16, 17):
                raise ValueError("Fantasy hidden incoming count must be 0 or 14..17")
        elif self.hidden_incoming_count not in (0, 3, 5):
            raise ValueError("normal hidden incoming count must be 0, 3 or 5")


@dataclass(frozen=True)
class RawOFCObservation:
    """Frame-level visual observation before strategic interpretation.

    In normal play this layer intentionally does not say which Hero row cards
    are committed; the stateful reconstructor uses previous state plus the
    discard tracker.

    In active Hero Fantasy the semantics are different and intentionally
    self-contained: every visible Hero row card is tentative, every remaining
    current card is loose in the 14..17-card Fantasy set, and `round_index=-1`.
    This lets DeepOFC attach safely to a fresh/mid-arrangement Fantasy frame
    without pretending it is normal round 3/4 merely because 14/17 physical
    cards happen to be visible.

    KKPoker replay evidence shows the gold Confirm button while the earlier
    opponent's timer is still active. Therefore `confirm_visible` is a raw UI
    fact and is deliberately different from canonical `hero_can_confirm`.
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
        if self.mode != "joker_ultimate":
            raise ValueError("raw DeepOFC runtime mode must be joker_ultimate")

        visible = []
        for p in self.players:
            visible.extend(p.visual_board.cards())
        visible.extend(self.hero_loose_cards)
        visible.extend(self.hero_discard_tracker)
        # Tentative Hero cards can be visible in a row instead of loose, but a
        # physical card must never be visible simultaneously in two places.
        if len(visible) != len(set(visible)):
            raise ValueError("duplicate physical card in raw visual observation")

        hero = self.player(self.hero_chair)
        if hero.fantasy:
            if self.round_index != -1:
                raise ValueError("active Hero Fantasy requires round_index=-1")
            # During the active one-shot arrangement, unused current Fantasy
            # cards remain loose. The current hand's discard tracker is populated
            # only after Confirm, as proven by supplied frames 53 -> 54.
            if self.hero_discard_tracker:
                raise ValueError(
                    "active pre-Confirm Hero Fantasy must keep unused cards loose, not in discard tracker"
                )
            total_current = hero.visual_board.filled_count() + len(self.hero_loose_cards)
            if total_current not in range(14, 18):
                raise ValueError(
                    f"active Hero Fantasy must expose exactly 14..17 current cards, got {total_current}"
                )
        else:
            if self.round_index not in range(5):
                raise ValueError("normal round_index must be 0..4")
            derived_round = derive_normal_round_index(
                hero_visual_board_count=hero.visual_board.filled_count(),
                hero_loose_count=len(self.hero_loose_cards),
                hero_discard_tracker_count=len(self.hero_discard_tracker),
            )
            if derived_round != self.round_index:
                raise ValueError(
                    f"round_index={self.round_index} contradicts Hero visible-card accounting round={derived_round}"
                )

    @property
    def hero_is_fantasy(self) -> bool:
        return self.player(self.hero_chair).fantasy

    def player(self, chair: int) -> RawPlayerObservation:
        for p in self.players:
            if p.chair == chair:
                return p
        raise KeyError(chair)
