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


# Fixed first two rounds. These are not an abstraction of hidden information:
# they are a certified public/private checkpoint built by the canonical R4
# sequential engine before the R6 chance support begins at round_index=2.
PRIOR_HANDS = (
    (
        (C("2c"), C("4c"), C("5d"), C("6h"), C("7s")),
        (C("8c"), C("3s"), C("Ac")),
    ),
    (
        (C("2h"), C("4h"), C("5s"), C("6c"), C("7d")),
        (C("8h"), C("3d"), C("Ah")),
    ),
)

PRIOR_ACTIONS = (
    (
        NormalPlacementAction(
            placements=(
                P("2c", Row.TOP),
                P("4c", Row.MIDDLE), P("5d", Row.MIDDLE),
                P("6h", Row.MIDDLE), P("7s", Row.MIDDLE),
            )
        ),
        NormalPlacementAction(
            placements=(P("8c", Row.MIDDLE), P("3s", Row.BOTTOM)),
            discard=C("Ac"),
        ),
    ),
    (
        NormalPlacementAction(
            placements=(
                P("2h", Row.TOP),
                P("4h", Row.MIDDLE), P("5s", Row.MIDDLE),
                P("6c", Row.MIDDLE), P("7d", Row.MIDDLE),
            )
        ),
        NormalPlacementAction(
            placements=(P("8h", Row.MIDDLE), P("3d", Row.BOTTOM)),
            discard=C("Ah"),
        ),
    ),
)

# Every future P0 ordinary card is a spade; P1 receives the suit-mirrored
# diamonds. With Middle frozen as an 8-high straight and Bottom starting with a
# suited 3, every legal terminal is non-foul: Top can be at most trips, while
# Bottom necessarily becomes a flush-or-better after four future placements.
P0_FUTURE_SCHEDULES = (
    (
        (C("2s"), C("4s"), C("JK1")),
        (C("6s"), C("8s"), C("9s")),
        (C("Ts"), C("Qs"), C("Ks")),
    ),
    (
        (C("2s"), C("6s"), C("Ts")),
        (C("4s"), C("8s"), C("Qs")),
        (C("9s"), C("Ks"), C("JK1")),
    ),
)

P1_FUTURE_SCHEDULES = (
    (
        (C("2d"), C("4d"), C("JK2")),
        (C("6d"), C("8d"), C("9d")),
        (C("Td"), C("Qd"), C("Kd")),
    ),
    (
        (C("2d"), C("6d"), C("Td")),
        (C("4d"), C("8d"), C("Qd")),
        (C("9d"), C("Kd"), C("JK2")),
    ),
)


@dataclass(frozen=True)
class ThreeRoundChanceOutcome:
    p0_variant: int
    p1_variant: int
    first_player: int

    def __post_init__(self) -> None:
        if self.p0_variant not in (0, 1) or self.p1_variant not in (0, 1):
            raise ValueError("three-round chance variants must be 0 or 1")
        if self.first_player not in (0, 1):
            raise ValueError("first_player must be 0 or 1")

    def mirrored_swapped(self) -> "ThreeRoundChanceOutcome":
        return ThreeRoundChanceOutcome(
            p0_variant=self.p1_variant,
            p1_variant=self.p0_variant,
            first_player=1 - self.first_player,
        )


StrategyProfile = Mapping[
    HUPlayerObservation,
    Mapping[NormalPlacementAction, float],
]


class HUThreeRoundSequentialSubgame:
    """Three-decision-per-player HU benchmark on the canonical R4 engine."""

    exact_reference_value = 0.0

    def __init__(self) -> None:
        self.outcomes = tuple(
            ThreeRoundChanceOutcome(v0, v1, first)
            for v0, v1, first in product(range(2), repeat=3)
        )
        self.chance_probability = 1.0 / len(self.outcomes)
        self._support = set(self.outcomes)

    def _future_hands(self, outcome: ThreeRoundChanceOutcome):
        return (
            P0_FUTURE_SCHEDULES[outcome.p0_variant],
            P1_FUTURE_SCHEDULES[outcome.p1_variant],
        )

    @lru_cache(maxsize=None)
    def initial_state(self, outcome: ThreeRoundChanceOutcome) -> HUSequentialNormalState:
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
            raise AssertionError("three-round fixture must serialize 34 unique drawn cards")
        remaining = [card for card in PHYSICAL_DECK_54 if card not in set(drawn)]
        order = tuple((*drawn, *remaining))
        if len(order) != 54 or len(set(order)) != 54:
            raise AssertionError("three-round fixture deck must be one physical 54-card permutation")

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

        # Replay the fixed first two rounds through the same engine used by live
        # benchmark transitions. This certifies the checkpoint rather than
        # constructing partial boards independently of R4 semantics.
        while state.round_index < 2:
            chair = state.acting_chair
            action = PRIOR_ACTIONS[chair][state.round_index]
            state = state.apply(action)

        expected_current = future[0][0], future[1][0]
        if state.round_index != 2 or state.actor_in_round != 0:
            raise AssertionError("three-round checkpoint did not land at start of round 2")
        if state.incoming != expected_current:
            raise AssertionError("three-round checkpoint future deal serialization mismatch")
        return state

    @lru_cache(maxsize=None)
    def actions(self, info: HUPlayerObservation) -> tuple[NormalPlacementAction, ...]:
        return enumerate_normal_actions(info.state)

    def info(self, state: HUSequentialNormalState) -> HUPlayerObservation:
        if state.terminal:
            raise ValueError("terminal state has no information set")
        return state.observation(state.acting_chair)

    def distribution(
        self,
        profile: StrategyProfile,
        info: HUPlayerObservation,
    ) -> dict[NormalPlacementAction, float]:
        legal = self.actions(info)
        supplied = profile.get(info)
        if supplied is None:
            p = 1.0 / len(legal)
            return {action: p for action in legal}
        illegal = set(supplied) - set(legal)
        if illegal:
            raise ValueError("strategy contains illegal three-round actions")
        weights = {action: float(supplied.get(action, 0.0)) for action in legal}
        if any(value < 0.0 for value in weights.values()):
            raise ValueError("strategy probabilities cannot be negative")
        total = sum(weights.values())
        if total <= 0.0:
            raise ValueError("strategy needs positive probability mass")
        return {action: value / total for action, value in weights.items()}

    def terminal_u0(self, state: HUSequentialNormalState) -> int:
        if not state.terminal:
            raise ValueError("terminal utility requires terminal state")
        if is_foul(state.boards[0], equality_allowed=True) or is_foul(
            state.boards[1], equality_allowed=True
        ):
            raise AssertionError("three-round fixture was designed to exclude all foul terminals")
        return settle_raw_points(state.boards, equality_allowed=True).points_by_chair[0]

    def expected_u0(self, profile: StrategyProfile) -> float:
        def recurse(state: HUSequentialNormalState) -> float:
            if state.terminal:
                return float(self.terminal_u0(state))
            info = self.info(state)
            return sum(
                probability * recurse(state.apply(action))
                for action, probability in self.distribution(profile, info).items()
            )

        return self.chance_probability * sum(
            recurse(self.initial_state(outcome)) for outcome in self.outcomes
        )

    def terminal_count(self) -> int:
        def recurse(state: HUSequentialNormalState) -> int:
            if state.terminal:
                return 1
            return sum(recurse(state.apply(action)) for action in state.legal_actions())

        return sum(recurse(self.initial_state(outcome)) for outcome in self.outcomes)

    def collect_infosets(self) -> dict[HUPlayerObservation, tuple[NormalPlacementAction, ...]]:
        infos: dict[HUPlayerObservation, tuple[NormalPlacementAction, ...]] = {}

        def recurse(state: HUSequentialNormalState) -> None:
            if state.terminal:
                return
            info = self.info(state)
            legal = self.actions(info)
            existing = infos.setdefault(info, legal)
            if existing != legal:
                raise AssertionError("same sequential infoset produced different legal action sets")
            for action in legal:
                recurse(state.apply(action))

        for outcome in self.outcomes:
            recurse(self.initial_state(outcome))
        return infos

    def assert_terminal_swap_symmetry(self) -> int:
        checks = 0
        for outcome in self.outcomes:
            mirrored_outcome = outcome.mirrored_swapped()
            if mirrored_outcome not in self._support:
                raise AssertionError("three-round mirrored chance outcome missing")
            left_root = self.initial_state(outcome)
            right_root = self.initial_state(mirrored_outcome)

            def recurse(left: HUSequentialNormalState, right: HUSequentialNormalState) -> None:
                nonlocal checks
                if left.terminal:
                    if not right.terminal:
                        raise AssertionError("mirrored three-round state is not terminal")
                    u0 = self.terminal_u0(left)
                    mirror_u0 = self.terminal_u0(right)
                    if u0 != -mirror_u0:
                        raise AssertionError(
                            f"three-round payoff symmetry failed: {u0} vs {mirror_u0}"
                        )
                    checks += 1
                    return
                if right.terminal:
                    raise AssertionError("mirrored three-round state terminated early")
                if right.acting_chair != 1 - left.acting_chair:
                    raise AssertionError("three-round actor swap symmetry failed")

                right_keys = {
                    candidate.key(): candidate for candidate in right.legal_actions()
                }
                for action in left.legal_actions():
                    mirrored_action = joker_mirror_action(action)
                    candidate = right_keys.get(mirrored_action.key())
                    if candidate is None:
                        raise AssertionError("mirrored three-round action is not legal")
                    recurse(left.apply(action), right.apply(candidate))

            recurse(left_root, right_root)
        return checks
