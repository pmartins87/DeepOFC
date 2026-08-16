from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from itertools import product
from typing import Mapping

from .actions import NormalPlacementAction, enumerate_normal_actions
from .hu_two_round_joker import joker_mirror_action
from .scoring import is_foul
from .sequential import HUPlayerObservation, HUSequentialNormalState
from .simulator import DeterministicDeck, PHYSICAL_DECK_54, settle_raw_points
from .state import Card, PendingPlacement, PlayerBoard, Row


def C(code: str) -> Card:
    return Card.from_code(code)


def P(code: str, row: Row) -> PendingPlacement:
    return PendingPlacement(card=C(code), row=row)


# Two fixed/certified normal rounds. After replay, each player has:
#   Top    = complete A-3-2 high-card row (3 cards)
#   Middle = pair of 4s + 5 + 6 (4 cards, one vacancy)
#   Bottom = empty (5 vacancies)
# Thus exactly one of the six future placements must go to Middle and five to
# Bottom. All possible future ordinary cards are one suit per player, with one
# persistent physical Joker. Bottom is therefore always flush-or-better, Middle
# is at most trips, and Top is high-card: every legal terminal is non-foul.
PRIOR_HANDS = (
    (
        (C("2c"), C("3c"), C("Ac"), C("4c"), C("5c")),
        (C("4d"), C("6c"), C("Kc")),
    ),
    (
        (C("2h"), C("3h"), C("Ah"), C("4h"), C("5h")),
        (C("4s"), C("6h"), C("Kh")),
    ),
)

PRIOR_ACTIONS = (
    (
        NormalPlacementAction(
            placements=(
                P("2c", Row.TOP), P("3c", Row.TOP), P("Ac", Row.TOP),
                P("4c", Row.MIDDLE), P("5c", Row.MIDDLE),
            )
        ),
        NormalPlacementAction(
            placements=(P("4d", Row.MIDDLE), P("6c", Row.MIDDLE)),
            discard=C("Kc"),
        ),
    ),
    (
        NormalPlacementAction(
            placements=(
                P("2h", Row.TOP), P("3h", Row.TOP), P("Ah", Row.TOP),
                P("4h", Row.MIDDLE), P("5h", Row.MIDDLE),
            )
        ),
        NormalPlacementAction(
            placements=(P("4s", Row.MIDDLE), P("6h", Row.MIDDLE)),
            discard=C("Kh"),
        ),
    ),
)

# Current round (round_index=2) is intentionally identical across every chance
# variant. Therefore the player's present private hand cannot reveal which
# future chance branch was selected.
ROUND2_FIXED = (
    (C("7s"), C("8s"), C("9s")),
    (C("7d"), C("8d"), C("9d")),
)

# Round-3 private hand reveals only the player's own r3 bit. It does NOT reveal
# the independently sampled r4 bit, so real future private-card uncertainty
# survives between the second and third decisions.
ROUND3_OPTIONS = (
    (
        (C("Ts"), C("Js"), C("Qs")),
        (C("Ts"), C("Js"), C("Ks")),
    ),
    (
        (C("Td"), C("Jd"), C("Qd")),
        (C("Td"), C("Jd"), C("Kd")),
    ),
)

ROUND4_OPTIONS = (
    (
        (C("As"), C("5s"), C("6s")),
        (C("As"), C("5s"), C("JK1")),
    ),
    (
        (C("Ad"), C("5d"), C("6d")),
        (C("Ad"), C("5d"), C("JK2")),
    ),
)


@dataclass(frozen=True)
class ThreeRoundChanceOutcomeV2:
    p0_r3_variant: int
    p0_r4_variant: int
    p1_r3_variant: int
    p1_r4_variant: int
    first_player: int

    def __post_init__(self) -> None:
        bits = (
            self.p0_r3_variant,
            self.p0_r4_variant,
            self.p1_r3_variant,
            self.p1_r4_variant,
            self.first_player,
        )
        if any(bit not in (0, 1) for bit in bits):
            raise ValueError("three-round V2 chance coordinates must be binary")

    def r3_variant(self, player: int) -> int:
        return self.p0_r3_variant if player == 0 else self.p1_r3_variant

    def r4_variant(self, player: int) -> int:
        return self.p0_r4_variant if player == 0 else self.p1_r4_variant

    def mirrored_swapped(self) -> "ThreeRoundChanceOutcomeV2":
        return ThreeRoundChanceOutcomeV2(
            p0_r3_variant=self.p1_r3_variant,
            p0_r4_variant=self.p1_r4_variant,
            p1_r3_variant=self.p0_r3_variant,
            p1_r4_variant=self.p0_r4_variant,
            first_player=1 - self.first_player,
        )


StrategyProfileV2 = Mapping[
    HUPlayerObservation,
    Mapping[NormalPlacementAction, float],
]


class HUThreeRoundSequentialSubgameV2:
    """Three-decision HU benchmark with independent future private chance.

    Compared with V1, the current round no longer identifies the future private
    schedule, and P0/P1 future chance bits are independent. This removes a
    representativeness flaw before solver-architecture conclusions are drawn.
    """

    exact_reference_value = 0.0

    def __init__(self) -> None:
        self.outcomes = tuple(
            ThreeRoundChanceOutcomeV2(a, b, c, d, first)
            for a, b, c, d, first in product(range(2), repeat=5)
        )
        self.chance_probability = 1.0 / len(self.outcomes)
        self._support = set(self.outcomes)

    def _future_hands(self, outcome: ThreeRoundChanceOutcomeV2):
        return (
            (
                ROUND2_FIXED[0],
                ROUND3_OPTIONS[0][outcome.p0_r3_variant],
                ROUND4_OPTIONS[0][outcome.p0_r4_variant],
            ),
            (
                ROUND2_FIXED[1],
                ROUND3_OPTIONS[1][outcome.p1_r3_variant],
                ROUND4_OPTIONS[1][outcome.p1_r4_variant],
            ),
        )

    @lru_cache(maxsize=None)
    def initial_state(self, outcome: ThreeRoundChanceOutcomeV2) -> HUSequentialNormalState:
        future = self._future_hands(outcome)
        batches = (
            (PRIOR_HANDS[0][0], PRIOR_HANDS[0][1], *future[0]),
            (PRIOR_HANDS[1][0], PRIOR_HANDS[1][1], *future[1]),
        )
        drawn: list[Card] = []
        for round_index in range(5):
            first = outcome.first_player
            second = 1 - first
            drawn.extend(batches[first][round_index])
            drawn.extend(batches[second][round_index])
        if len(drawn) != 34 or len(set(drawn)) != 34:
            raise AssertionError("three-round V2 fixture must serialize 34 unique physical cards")
        remaining = [card for card in PHYSICAL_DECK_54 if card not in set(drawn)]
        order = tuple((*drawn, *remaining))
        if len(order) != 54 or len(set(order)) != 54:
            raise AssertionError("three-round V2 deck must be one 54-card permutation")

        deck = DeterministicDeck(order, 0)
        first_cards, deck = deck.draw(5)
        second_cards, deck = deck.draw(5)
        incoming: list[tuple[Card, ...]] = [(), ()]
        incoming[outcome.first_player] = first_cards
        incoming[1 - outcome.first_player] = second_cards
        state = HUSequentialNormalState(
            deck=deck,
            boards=(PlayerBoard(), PlayerBoard()),
            incoming=(incoming[0], incoming[1]),
            discards=((), ()),
            history=(),
            round_index=0,
            actor_in_round=0,
            first_player=outcome.first_player,
            dealer_chair=outcome.first_player,
            terminal=False,
        )
        while state.round_index < 2:
            state = state.apply(PRIOR_ACTIONS[state.acting_chair][state.round_index])

        if state.round_index != 2 or state.actor_in_round != 0:
            raise AssertionError("three-round V2 checkpoint did not land at round 2 root")
        if state.incoming != ROUND2_FIXED:
            raise AssertionError("three-round V2 current hands must be invariant across chance variants")
        return state

    @lru_cache(maxsize=None)
    def actions(self, info: HUPlayerObservation) -> tuple[NormalPlacementAction, ...]:
        return enumerate_normal_actions(info.state)

    def info(self, state: HUSequentialNormalState) -> HUPlayerObservation:
        if state.terminal:
            raise ValueError("terminal state has no information set")
        return state.observation(state.acting_chair)

    def transition(self, state: HUSequentialNormalState, action: NormalPlacementAction) -> HUSequentialNormalState:
        return state.apply_fast(action)

    def distribution(self, profile: StrategyProfileV2, info: HUPlayerObservation):
        legal = self.actions(info)
        supplied = profile.get(info)
        if supplied is None:
            p = 1.0 / len(legal)
            return {action: p for action in legal}
        illegal = set(supplied) - set(legal)
        if illegal:
            raise ValueError("strategy contains illegal V2 actions")
        values = {action: float(supplied.get(action, 0.0)) for action in legal}
        if any(value < 0.0 for value in values.values()):
            raise ValueError("strategy probabilities cannot be negative")
        total = sum(values.values())
        if total <= 0.0:
            raise ValueError("strategy needs positive probability mass")
        return {action: value / total for action, value in values.items()}

    def terminal_u0(self, state: HUSequentialNormalState) -> int:
        if not state.terminal:
            raise ValueError("terminal utility requires terminal state")
        if is_foul(state.boards[0], equality_allowed=True) or is_foul(state.boards[1], equality_allowed=True):
            raise AssertionError("three-round V2 was designed to exclude every foul terminal")
        return settle_raw_points(state.boards, equality_allowed=True).points_by_chair[0]

    def expected_u0(self, profile: StrategyProfileV2) -> float:
        def recurse(state: HUSequentialNormalState) -> float:
            if state.terminal:
                return float(self.terminal_u0(state))
            info = self.info(state)
            return sum(
                probability * recurse(self.transition(state, action))
                for action, probability in self.distribution(profile, info).items()
                if probability > 0.0
            )
        return self.chance_probability * sum(recurse(self.initial_state(outcome)) for outcome in self.outcomes)

    def assert_terminal_swap_symmetry(self) -> int:
        checks = 0
        for outcome in self.outcomes:
            mirror_outcome = outcome.mirrored_swapped()
            if mirror_outcome not in self._support:
                raise AssertionError("three-round V2 mirrored chance outcome missing")
            left_root = self.initial_state(outcome)
            right_root = self.initial_state(mirror_outcome)

            def recurse(left: HUSequentialNormalState, right: HUSequentialNormalState) -> None:
                nonlocal checks
                if left.terminal:
                    if not right.terminal:
                        raise AssertionError("three-round V2 mirror terminated asymmetrically")
                    left.assert_fully_valid()
                    right.assert_fully_valid()
                    u0 = self.terminal_u0(left)
                    mirror_u0 = self.terminal_u0(right)
                    if u0 != -mirror_u0:
                        raise AssertionError(f"three-round V2 payoff symmetry failed: {u0} vs {mirror_u0}")
                    checks += 1
                    return
                if right.terminal or right.acting_chair != 1 - left.acting_chair:
                    raise AssertionError("three-round V2 actor/terminal mirror mismatch")
                left_info, right_info = self.info(left), self.info(right)
                right_by_key = {a.key(): a for a in self.actions(right_info)}
                for action in self.actions(left_info):
                    mirrored = joker_mirror_action(action)
                    candidate = right_by_key.get(mirrored.key())
                    if candidate is None:
                        raise AssertionError("three-round V2 mirrored action is illegal")
                    recurse(self.transition(left, action), self.transition(right, candidate))

            recurse(left_root, right_root)
        return checks
