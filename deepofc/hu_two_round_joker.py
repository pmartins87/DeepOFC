from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from itertools import product

from .actions import NormalPlacementAction
from .hu_two_round import (
    HUTwoRoundSubgame,
    TwoRoundInfoSet,
    _actions_for,
    _apply,
    _split_actions,
)
from .state import Card, PendingPlacement, PlayerBoard


SUIT_MIRROR = {"c": "h", "h": "c", "d": "s", "s": "d"}


def _cards(codes: tuple[str, ...]) -> tuple[Card, ...]:
    return tuple(Card.from_code(code) for code in codes)


# Nine committed cards per player, leaving exactly the final two Pineapple rounds.
# Middle is already complete and fixed at one pair of 4s. Top has two distinct
# low cards; Bottom already has a pair of Kings. Therefore every legal placement
# in this benchmark remains non-foul even when a physical Joker is put on Top:
#   Bottom >= pair K > Middle pair 4 > Top high-card / pair 3.
JOKER_BASE_BOARDS = (
    PlayerBoard(
        top=_cards(("2c", "3d")),
        middle=_cards(("4c", "4d", "5c", "6d", "7c")),
        bottom=_cards(("Kc", "Kd")),
    ),
    PlayerBoard(
        top=_cards(("2h", "3s")),
        middle=_cards(("4h", "4s", "5h", "6s", "7h")),
        bottom=_cards(("Kh", "Ks")),
    ),
)

# Overlapping round-3 support makes the same public 8/9 placement compatible
# with either a hidden physical Joker discard or a hidden ordinary-card discard.
JOKER_ROUND3_HANDS = (
    (
        _cards(("8c", "9d", "JK1")),
        _cards(("8c", "9d", "Tc")),
    ),
    (
        _cards(("8h", "9s", "JK2")),
        _cards(("8h", "9s", "Th")),
    ),
)

JOKER_ROUND4_HANDS = (
    (
        _cards(("Jc", "Qd", "Ad")),
        _cards(("Jd", "Qc", "Ac")),
    ),
    (
        _cards(("Jh", "Qs", "As")),
        _cards(("Js", "Qh", "Ah")),
    ),
)


def joker_mirror_card(card: Card) -> Card:
    """Audit automorphism only; never a runtime Joker-identity normalization."""
    if card.is_joker:
        assert card.joker_id in (1, 2)
        return Card(joker_id=3 - card.joker_id)
    assert card.rank is not None and card.suit is not None
    return Card(rank=card.rank, suit=SUIT_MIRROR[card.suit])


def joker_mirror_action(action: NormalPlacementAction) -> NormalPlacementAction:
    return NormalPlacementAction(
        placements=tuple(
            PendingPlacement(card=joker_mirror_card(p.card), row=p.row)
            for p in action.placements
        ),
        discard=(
            None if action.discard is None else joker_mirror_card(action.discard)
        ),
    )


@dataclass(frozen=True)
class JokerTwoRoundChanceOutcome:
    round3_hand0: tuple[Card, ...]
    round3_hand1: tuple[Card, ...]
    round4_hand0: tuple[Card, ...]
    round4_hand1: tuple[Card, ...]
    first_player: int

    @property
    def second_player(self) -> int:
        return 1 - self.first_player

    def hand(self, player: int, round_index: int) -> tuple[Card, ...]:
        if round_index == 3:
            return self.round3_hand0 if player == 0 else self.round3_hand1
        if round_index == 4:
            return self.round4_hand0 if player == 0 else self.round4_hand1
        raise ValueError("Joker two-round benchmark supports round 3 or 4")

    def mirrored_swapped(self) -> "JokerTwoRoundChanceOutcome":
        return JokerTwoRoundChanceOutcome(
            round3_hand0=tuple(joker_mirror_card(c) for c in self.round3_hand1),
            round3_hand1=tuple(joker_mirror_card(c) for c in self.round3_hand0),
            round4_hand0=tuple(joker_mirror_card(c) for c in self.round4_hand1),
            round4_hand1=tuple(joker_mirror_card(c) for c in self.round4_hand0),
            first_player=1 - self.first_player,
        )


class HUTwoRoundJokerSubgame(HUTwoRoundSubgame):
    """Reduced two-decision HU benchmark with persistent physical Jokers."""

    def __init__(self) -> None:
        outcomes: list[JokerTwoRoundChanceOutcome] = []
        for r3_0, r3_1, r4_0, r4_1, first in product(range(2), repeat=5):
            outcome = JokerTwoRoundChanceOutcome(
                round3_hand0=JOKER_ROUND3_HANDS[0][r3_0],
                round3_hand1=JOKER_ROUND3_HANDS[1][r3_1],
                round4_hand0=JOKER_ROUND4_HANDS[0][r4_0],
                round4_hand1=JOKER_ROUND4_HANDS[1][r4_1],
                first_player=first,
            )
            # Physical uniqueness is part of the benchmark definition, not an
            # assumption delegated to the scorer.
            known = (
                *JOKER_BASE_BOARDS[0].cards(),
                *JOKER_BASE_BOARDS[1].cards(),
                *outcome.round3_hand0,
                *outcome.round3_hand1,
                *outcome.round4_hand0,
                *outcome.round4_hand1,
            )
            if len(known) != len(set(known)):
                raise AssertionError("Joker benchmark chance outcome duplicates a physical card")
            outcomes.append(outcome)
        self.outcomes = tuple(outcomes)
        if len(self.outcomes) != 32:
            raise AssertionError("Joker two-round support must contain 32 outcomes")
        self.chance_probability = 1.0 / len(self.outcomes)
        self.info_actions = self._build_info_actions()

    @lru_cache(maxsize=None)
    def _round3_actions(
        self,
        outcome: JokerTwoRoundChanceOutcome,
        player: int,
    ) -> tuple[NormalPlacementAction, ...]:
        return _actions_for(
            player,
            JOKER_BASE_BOARDS[0],
            JOKER_BASE_BOARDS[1],
            outcome.hand(player, 3),
            3,
        )

    @lru_cache(maxsize=None)
    def _boards_after_round3(
        self,
        outcome: JokerTwoRoundChanceOutcome,
        first_action: NormalPlacementAction,
        second_action: NormalPlacementAction,
    ):
        action0, action1 = _split_actions(
            outcome.first_player, first_action, second_action
        )
        board0 = _apply(JOKER_BASE_BOARDS[0], action0, outcome.round3_hand0, 3)
        board1 = _apply(JOKER_BASE_BOARDS[1], action1, outcome.round3_hand1, 3)
        return board0, board1, action0, action1

    def assert_terminal_swap_symmetry(self) -> int:
        support = set(self.outcomes)
        checks = 0
        for outcome in self.outcomes:
            mirrored = outcome.mirrored_swapped()
            if mirrored not in support:
                raise AssertionError("mirrored-swapped Joker outcome missing")
            first = outcome.first_player
            second = outcome.second_player
            for first_r3 in self._round3_actions(outcome, first):
                for second_r3 in self._round3_actions(outcome, second):
                    board0, board1, _, _ = self._boards_after_round3(
                        outcome, first_r3, second_r3
                    )
                    for first_r4 in self._round4_actions(
                        outcome, first, board0, board1
                    ):
                        for second_r4 in self._round4_actions(
                            outcome, second, board0, board1
                        ):
                            u0 = self.terminal_u0(
                                outcome, first_r3, second_r3, first_r4, second_r4
                            )
                            mirror_u0 = self.terminal_u0(
                                mirrored,
                                joker_mirror_action(first_r3),
                                joker_mirror_action(second_r3),
                                joker_mirror_action(first_r4),
                                joker_mirror_action(second_r4),
                            )
                            if u0 != -mirror_u0:
                                raise AssertionError(
                                    "Joker terminal symmetry failed: "
                                    f"u0={u0} mirror={mirror_u0}"
                                )
                            checks += 1
        return checks
