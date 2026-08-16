from __future__ import annotations

from itertools import product

from .hu_two_round import HUTwoRoundSubgame, TwoRoundChanceOutcome
from .state import Card


def _cards(codes: tuple[str, ...]) -> tuple[Card, ...]:
    return tuple(Card.from_code(code) for code in codes)


# Third R6 benchmark fixture. Unlike the earlier two-round support, the two
# round-3 private-hand variants overlap in the same two publicly placeable cards.
# Consequently a public placement such as 6c/7c can be compatible with either
# hidden discard 8c or 8d. The player-swap automorphism remains suit-only:
# c<->h and d<->s, so poker rank order is preserved exactly.
HIDDEN_DISCARD_ROUND3_HANDS = (
    (
        _cards(("6c", "7c", "8c")),
        _cards(("6c", "7c", "8d")),
    ),
    (
        _cards(("6h", "7h", "8h")),
        _cards(("6h", "7h", "8s")),
    ),
)

# Round 4 keeps the already certified disjoint-rank support. These cards remain
# private at the decision and provide a second independent source of hidden
# information; no rank repeats can create a Middle two-pair foul branch.
HIDDEN_DISCARD_ROUND4_HANDS = (
    (
        _cards(("9c", "Tc", "Jc")),
        _cards(("9d", "Td", "Jd")),
    ),
    (
        _cards(("9h", "Th", "Jh")),
        _cards(("9s", "Ts", "Js")),
    ),
)


class HUTwoRoundHiddenDiscardSubgame(HUTwoRoundSubgame):
    """Two-decision HU benchmark with strategically ambiguous hidden discards."""

    def __init__(self) -> None:
        outcomes: list[TwoRoundChanceOutcome] = []
        for r3_0, r3_1, r4_0, r4_1, first in product(range(2), repeat=5):
            outcomes.append(
                TwoRoundChanceOutcome(
                    round3_hand0=HIDDEN_DISCARD_ROUND3_HANDS[0][r3_0],
                    round3_hand1=HIDDEN_DISCARD_ROUND3_HANDS[1][r3_1],
                    round4_hand0=HIDDEN_DISCARD_ROUND4_HANDS[0][r4_0],
                    round4_hand1=HIDDEN_DISCARD_ROUND4_HANDS[1][r4_1],
                    first_player=first,
                )
            )
        self.outcomes = tuple(outcomes)
        if len(self.outcomes) != 32:
            raise AssertionError("hidden-discard chance support must contain 32 outcomes")
        self.chance_probability = 1.0 / len(self.outcomes)
        self.info_actions = self._build_info_actions()
