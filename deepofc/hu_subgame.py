from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations
from typing import Mapping

from .actions import NormalPlacementAction
from .simulator import apply_normal_action, settle_raw_points
from .state import Card, PendingPlacement, PlayerBoard, Row


# This deliberately small R6 benchmark is a real OFC final-round placement
# problem, not a poker-like toy with unrelated actions. Both players have 11
# committed cards, receive three private cards, place two and discard one. The
# first player's confirmed placements are public before the second player acts;
# the first player's discard remains private.
#
# The two fixed boards are exact suit mirrors. The eight-card chance pool is
# closed under the same suit involution, and chance chooses the first actor with
# probability 1/2. Swapping players + mirroring suits + flipping actor order is
# therefore an automorphism that negates terminal utility. The two-player
# zero-sum game consequently has exact value 0 before rake/cash economics.

SUIT_MIRROR = {"c": "d", "d": "c", "h": "s", "s": "h"}


def _cards(codes: tuple[str, ...]) -> tuple[Card, ...]:
    return tuple(Card.from_code(code) for code in codes)


BASE_BOARDS = (
    PlayerBoard(
        top=_cards(("2c", "3c")),
        middle=_cards(("4c", "5c", "6c", "7c")),
        bottom=_cards(("8c", "9c", "Tc", "Jc", "Qc")),
    ),
    PlayerBoard(
        top=_cards(("2d", "3d")),
        middle=_cards(("4d", "5d", "6d", "7d")),
        bottom=_cards(("8d", "9d", "Td", "Jd", "Qd")),
    ),
)

CHANCE_POOL = _cards(("Kc", "Kd", "Kh", "Ks", "Ac", "Ad", "Ah", "As"))


def mirror_card_code(code: str) -> str:
    card = Card.from_code(code)
    if card.is_joker:
        raise ValueError("R6 symmetric subgame does not use Jokers")
    assert card.rank is not None and card.suit is not None
    return Card(rank=card.rank, suit=SUIT_MIRROR[card.suit]).code


def hand_key(cards: tuple[Card, ...] | tuple[str, ...]) -> tuple[str, ...]:
    codes = tuple(card.code if isinstance(card, Card) else card for card in cards)
    return tuple(sorted(codes))


@dataclass(frozen=True, order=True)
class HUPlacementAction:
    """Abstract label for the real final-round place-two/discard-one action."""

    top: str
    middle: str
    discard: str

    @property
    def public_key(self) -> tuple[str, str]:
        # Only confirmed placements are public. The discarded card is private.
        return (self.top, self.middle)

    def mirrored(self) -> "HUPlacementAction":
        return HUPlacementAction(
            top=mirror_card_code(self.top),
            middle=mirror_card_code(self.middle),
            discard=mirror_card_code(self.discard),
        )


@dataclass(frozen=True, order=True)
class HUInfoSet:
    player: int
    role: str  # "first" or "second"
    private_hand: tuple[str, ...]
    observed_top: str | None = None
    observed_middle: str | None = None

    def __post_init__(self) -> None:
        if self.player not in (0, 1):
            raise ValueError("HU player must be 0 or 1")
        if self.role not in {"first", "second"}:
            raise ValueError("role must be first or second")
        if self.role == "first" and (
            self.observed_top is not None or self.observed_middle is not None
        ):
            raise ValueError("first actor cannot have an observed prior placement")
        if self.role == "second" and (
            self.observed_top is None or self.observed_middle is None
        ):
            raise ValueError("second actor must observe the first actor placements")


@dataclass(frozen=True)
class HUChanceOutcome:
    hand0: tuple[str, ...]
    hand1: tuple[str, ...]
    first_player: int

    @property
    def second_player(self) -> int:
        return 1 - self.first_player

    def hand(self, player: int) -> tuple[str, ...]:
        return self.hand0 if player == 0 else self.hand1

    def mirrored_swapped(self) -> "HUChanceOutcome":
        return HUChanceOutcome(
            hand0=tuple(sorted(mirror_card_code(code) for code in self.hand1)),
            hand1=tuple(sorted(mirror_card_code(code) for code in self.hand0)),
            first_player=1 - self.first_player,
        )


StrategyProfile = Mapping[HUInfoSet, Mapping[HUPlacementAction, float]]


def actions_for_hand(hand: tuple[str, ...]) -> tuple[HUPlacementAction, ...]:
    if len(hand) != 3 or len(set(hand)) != 3:
        raise ValueError("reduced HU final-round hand must contain three unique cards")
    actions: list[HUPlacementAction] = []
    for top in hand:
        for middle in hand:
            if middle == top:
                continue
            discard = next(card for card in hand if card not in {top, middle})
            actions.append(HUPlacementAction(top=top, middle=middle, discard=discard))
    return tuple(sorted(actions))


def _normal_action(action: HUPlacementAction) -> NormalPlacementAction:
    return NormalPlacementAction(
        placements=(
            PendingPlacement(Card.from_code(action.top), Row.TOP),
            PendingPlacement(Card.from_code(action.middle), Row.MIDDLE),
        ),
        discard=Card.from_code(action.discard),
    )


@lru_cache(maxsize=None)
def _completed_board(
    player: int,
    private_hand: tuple[str, ...],
    action: HUPlacementAction,
) -> PlayerBoard:
    incoming = tuple(Card.from_code(code) for code in private_hand)
    board, discards = apply_normal_action(
        BASE_BOARDS[player],
        _normal_action(action),
        round_index=4,
        incoming=incoming,
    )
    if len(discards) != 1 or discards[0].code != action.discard:
        raise AssertionError("reduced action discard mismatch")
    if not board.is_complete():
        raise AssertionError("reduced final-round action must complete the board")
    return board


@lru_cache(maxsize=None)
def _terminal_u0(
    hand0: tuple[str, ...],
    hand1: tuple[str, ...],
    action0: HUPlacementAction,
    action1: HUPlacementAction,
) -> int:
    board0 = _completed_board(0, hand0, action0)
    board1 = _completed_board(1, hand1, action1)
    return settle_raw_points((board0, board1)).points_by_chair[0]


class HUFinalRoundSubgame:
    """Small exact HU extensive-form benchmark for R6 architecture selection.

    Chance support:
      * choose P0's unordered 3-card hand from the 8-card reduced pool;
      * choose P1's unordered 3-card hand from the remaining five;
      * two cards remain undealt/unknown;
      * independently choose which player acts first with probability 1/2.

    Every resulting outcome is equiprobable. The second actor observes the two
    cards/rows confirmed by the first actor but does not observe the discarded
    third card, so multiple physical histories intentionally merge into one
    information set.
    """

    exact_reference_value: float = 0.0

    def __init__(self) -> None:
        pool_codes = tuple(card.code for card in CHANCE_POOL)
        outcomes: list[HUChanceOutcome] = []
        for h0 in combinations(pool_codes, 3):
            remaining = tuple(code for code in pool_codes if code not in h0)
            for h1 in combinations(remaining, 3):
                for first in (0, 1):
                    outcomes.append(
                        HUChanceOutcome(
                            hand0=tuple(sorted(h0)),
                            hand1=tuple(sorted(h1)),
                            first_player=first,
                        )
                    )
        self.outcomes = tuple(outcomes)
        if len(self.outcomes) != 1120:
            raise AssertionError(f"expected 1120 reduced chance outcomes, got {len(self.outcomes)}")
        self.chance_probability = 1.0 / len(self.outcomes)

        info_actions: dict[HUInfoSet, tuple[HUPlacementAction, ...]] = {}
        for outcome in self.outcomes:
            first = outcome.first_player
            second = outcome.second_player
            first_hand = outcome.hand(first)
            second_hand = outcome.hand(second)
            first_info = self.first_info(outcome)
            info_actions.setdefault(first_info, actions_for_hand(first_hand))
            for first_action in actions_for_hand(first_hand):
                second_info = self.second_info(outcome, first_action)
                info_actions.setdefault(second_info, actions_for_hand(second_hand))
        self.info_actions = dict(sorted(info_actions.items(), key=lambda item: item[0]))

    @staticmethod
    def first_info(outcome: HUChanceOutcome) -> HUInfoSet:
        player = outcome.first_player
        return HUInfoSet(
            player=player,
            role="first",
            private_hand=outcome.hand(player),
        )

    @staticmethod
    def second_info(
        outcome: HUChanceOutcome,
        first_action: HUPlacementAction,
    ) -> HUInfoSet:
        player = outcome.second_player
        return HUInfoSet(
            player=player,
            role="second",
            private_hand=outcome.hand(player),
            observed_top=first_action.top,
            observed_middle=first_action.middle,
        )

    def actions(self, info: HUInfoSet) -> tuple[HUPlacementAction, ...]:
        return self.info_actions[info]

    def terminal_u0(
        self,
        outcome: HUChanceOutcome,
        first_action: HUPlacementAction,
        second_action: HUPlacementAction,
    ) -> int:
        if outcome.first_player == 0:
            action0, action1 = first_action, second_action
        else:
            action0, action1 = second_action, first_action
        return _terminal_u0(outcome.hand0, outcome.hand1, action0, action1)

    def _distribution(
        self,
        profile: StrategyProfile,
        info: HUInfoSet,
    ) -> dict[HUPlacementAction, float]:
        legal = self.actions(info)
        supplied = profile.get(info)
        if supplied is None:
            probability = 1.0 / len(legal)
            return {action: probability for action in legal}
        illegal = set(supplied) - set(legal)
        if illegal:
            raise ValueError(f"strategy contains illegal actions at {info}: {sorted(illegal)}")
        weights = {action: float(supplied.get(action, 0.0)) for action in legal}
        if any(weight < 0.0 for weight in weights.values()):
            raise ValueError("strategy probabilities cannot be negative")
        total = sum(weights.values())
        if total <= 0.0:
            raise ValueError("strategy probabilities must have positive mass")
        return {action: weight / total for action, weight in weights.items()}

    def uniform_profile(self) -> dict[HUInfoSet, dict[HUPlacementAction, float]]:
        return {
            info: {action: 1.0 / len(actions) for action in actions}
            for info, actions in self.info_actions.items()
        }

    def expected_u0(self, profile: StrategyProfile) -> float:
        total = 0.0
        cp = self.chance_probability
        for outcome in self.outcomes:
            first_info = self.first_info(outcome)
            first_dist = self._distribution(profile, first_info)
            for first_action, p_first in first_dist.items():
                second_info = self.second_info(outcome, first_action)
                second_dist = self._distribution(profile, second_info)
                for second_action, p_second in second_dist.items():
                    total += (
                        cp
                        * p_first
                        * p_second
                        * self.terminal_u0(outcome, first_action, second_action)
                    )
        return total

    def best_response_value(self, profile: StrategyProfile, player: int) -> float:
        """Exact pure best-response value against one behavioral profile.

        Each player acts exactly once in this reduced game. Therefore a best
        response can be solved independently at every information set by summing
        counterfactual values of all indistinguishable physical histories and
        choosing the maximizing legal action. No sampling is used here.
        """

        if player not in (0, 1):
            raise ValueError("player must be 0 or 1")
        cp = self.chance_probability
        action_values: dict[HUInfoSet, dict[HUPlacementAction, float]] = {}

        # Histories where BR player acts first. Opponent's second action is
        # averaged under the supplied profile for each candidate public action.
        for outcome in self.outcomes:
            if outcome.first_player != player:
                continue
            info = self.first_info(outcome)
            bucket = action_values.setdefault(
                info, {action: 0.0 for action in self.actions(info)}
            )
            for first_action in self.actions(info):
                second_info = self.second_info(outcome, first_action)
                opp_dist = self._distribution(profile, second_info)
                continuation = 0.0
                for second_action, probability in opp_dist.items():
                    u0 = self.terminal_u0(outcome, first_action, second_action)
                    continuation += probability * (u0 if player == 0 else -u0)
                bucket[first_action] += cp * continuation

        # Histories where BR player acts second. Opponent's first action is part
        # of counterfactual reach; the BR action must be common to every hidden
        # history that merges into the same second-player information set.
        for outcome in self.outcomes:
            if outcome.second_player != player:
                continue
            first_info = self.first_info(outcome)
            opp_first_dist = self._distribution(profile, first_info)
            for first_action, p_first in opp_first_dist.items():
                info = self.second_info(outcome, first_action)
                bucket = action_values.setdefault(
                    info, {action: 0.0 for action in self.actions(info)}
                )
                for second_action in self.actions(info):
                    u0 = self.terminal_u0(outcome, first_action, second_action)
                    own = u0 if player == 0 else -u0
                    bucket[second_action] += cp * p_first * own

        return sum(max(values.values()) for values in action_values.values())

    def nash_conv(self, profile: StrategyProfile) -> float:
        return self.best_response_value(profile, 0) + self.best_response_value(profile, 1)

    def exploitability(self, profile: StrategyProfile) -> float:
        return 0.5 * self.nash_conv(profile)

    def count_merged_second_infosets(self) -> int:
        """Return how many second-player infosets merge >1 hidden histories."""
        histories: dict[HUInfoSet, set[tuple[tuple[str, ...], tuple[str, ...]]]] = {}
        for outcome in self.outcomes:
            first_hand = outcome.hand(outcome.first_player)
            for first_action in actions_for_hand(first_hand):
                info = self.second_info(outcome, first_action)
                histories.setdefault(info, set()).add((outcome.hand0, outcome.hand1))
        return sum(1 for values in histories.values() if len(values) > 1)

    def assert_terminal_swap_symmetry(self) -> int:
        """Exhaustively prove the terminal automorphism used for value=0.

        Returns the number of action-pair terminal branches checked.
        """

        outcome_set = set(self.outcomes)
        checks = 0
        for outcome in self.outcomes:
            mirrored = outcome.mirrored_swapped()
            if mirrored not in outcome_set:
                raise AssertionError("mirrored-swapped chance outcome missing from support")
            first_actions = actions_for_hand(outcome.hand(outcome.first_player))
            second_actions = actions_for_hand(outcome.hand(outcome.second_player))
            for first_action in first_actions:
                for second_action in second_actions:
                    u0 = self.terminal_u0(outcome, first_action, second_action)
                    mirrored_first = second_action.mirrored()
                    mirrored_second = first_action.mirrored()
                    mirrored_u0 = self.terminal_u0(
                        mirrored,
                        mirrored_first,
                        mirrored_second,
                    )
                    if u0 != -mirrored_u0:
                        raise AssertionError(
                            "terminal player-swap/suit-mirror symmetry failed: "
                            f"{outcome} {first_action} {second_action} -> {u0}, "
                            f"mirror -> {mirrored_u0}"
                        )
                    checks += 1
        return checks
