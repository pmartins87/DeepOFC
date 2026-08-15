from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from itertools import product
from typing import Mapping

from .actions import NormalPlacementAction, enumerate_normal_actions
from .simulator import apply_normal_action, settle_raw_points
from .state import Card, OFCState, PendingPlacement, PlayerBoard, PlayerState, Row


# Second R6 benchmark: two real later Pineapple rounds (round_index 3 and 4).
# Each player therefore acts twice and must remember its own first private hand,
# exact first action INCLUDING the hidden discard, and its newly received private
# hand. This is the first benchmark that forces perfect recall beyond the
# one-decision-per-player simplification in hu_subgame.py.
#
# The fixed boards and private supports use a rank-preserving suit-only mirror.
# Bottom starts KK/QQ, Middle starts 44 and private ranks are all distinct
# within each round and disjoint across rounds. Every legal terminal is
# therefore non-foul: Bottom two-pair always outranks Middle pair of 4s,
# which always outranks Top pair of 2s.
# Chance is intentionally a reduced, uniformly weighted support of 32 physically
# legal deal schedules rather than the full KKPoker deck law. The support is a
# product of independent binary hand variants for P0/P1 on each of two rounds,
# plus the first-actor bit. That keeps the tree exact and tractable while still
# leaving opponent private cards/discards genuinely unknown.

SUIT_MIRROR = {"c": "h", "h": "c", "d": "s", "s": "d"}


def _cards(codes: tuple[str, ...]) -> tuple[Card, ...]:
    return tuple(Card.from_code(code) for code in codes)


BASE_BOARDS = (
    PlayerBoard(
        top=_cards(("2c", "2d")),
        middle=_cards(("4c", "4d", "5c")),
        bottom=_cards(("Kc", "Kd", "Qc", "Qd")),
    ),
    PlayerBoard(
        top=_cards(("2h", "2s")),
        middle=_cards(("4h", "4s", "5h")),
        bottom=_cards(("Kh", "Ks", "Qh", "Qs")),
    ),
)

ROUND3_HANDS = (
    (
        _cards(("6c", "7c", "8c")),
        _cards(("6d", "7d", "8d")),
    ),
    (
        _cards(("6h", "7h", "8h")),
        _cards(("6s", "7s", "8s")),
    ),
)

ROUND4_HANDS = (
    (
        _cards(("9c", "Tc", "Jc")),
        _cards(("9d", "Td", "Jd")),
    ),
    (
        _cards(("9h", "Th", "Jh")),
        _cards(("9s", "Ts", "Js")),
    ),
)


def mirror_card(card: Card) -> Card:
    if card.is_joker:
        raise ValueError("two-round R6 benchmark does not use Jokers")
    assert card.rank is not None and card.suit is not None
    return Card(
        rank=card.rank,
        suit=SUIT_MIRROR[card.suit],
    )


def mirror_card_code(code: str) -> str:
    return mirror_card(Card.from_code(code)).code


@lru_cache(maxsize=None)
def action_public_key(action: NormalPlacementAction) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((placement.card.code, placement.row.value) for placement in action.placements))


def mirror_action(action: NormalPlacementAction) -> NormalPlacementAction:
    return NormalPlacementAction(
        placements=tuple(
            PendingPlacement(card=mirror_card(placement.card), row=placement.row)
            for placement in action.placements
        ),
        discard=None if action.discard is None else mirror_card(action.discard),
    )


@dataclass(frozen=True)
class TwoRoundChanceOutcome:
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
        raise ValueError("two-round benchmark supports round_index 3 or 4")

    def mirrored_swapped(self) -> "TwoRoundChanceOutcome":
        return TwoRoundChanceOutcome(
            round3_hand0=tuple(mirror_card(card) for card in self.round3_hand1),
            round3_hand1=tuple(mirror_card(card) for card in self.round3_hand0),
            round4_hand0=tuple(mirror_card(card) for card in self.round4_hand1),
            round4_hand1=tuple(mirror_card(card) for card in self.round4_hand0),
            first_player=1 - self.first_player,
        )


@dataclass(frozen=True)
class TwoRoundInfoSet:
    player: int
    round_index: int
    role: str
    own_round3_hand: tuple[str, ...]
    observed_current_first_public: tuple[tuple[str, str], ...] | None = None
    own_round3_action: tuple | None = None
    opponent_round3_public: tuple[tuple[str, str], ...] | None = None
    own_round4_hand: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        if self.player not in (0, 1):
            raise ValueError("player must be 0 or 1")
        if self.round_index not in (3, 4):
            raise ValueError("two-round infoset must be round 3 or 4")
        if self.role not in {"first", "second"}:
            raise ValueError("role must be first or second")
        if self.role == "first" and self.observed_current_first_public is not None:
            raise ValueError("first actor cannot observe a current prior action")
        if self.role == "second" and self.observed_current_first_public is None:
            raise ValueError("second actor must observe current first placements")
        if self.round_index == 3:
            if self.own_round3_action is not None:
                raise ValueError("round-3 decision cannot already contain own round-3 action")
            if self.opponent_round3_public is not None or self.own_round4_hand is not None:
                raise ValueError("round-3 infoset cannot contain future information")
        else:
            if self.own_round3_action is None:
                raise ValueError("round-4 infoset must remember own exact round-3 action")
            if self.opponent_round3_public is None:
                raise ValueError("round-4 infoset must remember opponent public round-3 placements")
            if self.own_round4_hand is None:
                raise ValueError("round-4 infoset must contain own new private hand")


StrategyProfile = Mapping[TwoRoundInfoSet, Mapping[NormalPlacementAction, float]]


def _codes(cards: tuple[Card, ...]) -> tuple[str, ...]:
    return tuple(sorted(card.code for card in cards))


@lru_cache(maxsize=None)
def _actions_for(
    player: int,
    board0: PlayerBoard,
    board1: PlayerBoard,
    incoming: tuple[Card, ...],
    round_index: int,
) -> tuple[NormalPlacementAction, ...]:
    state = OFCState(
        players=(
            PlayerState(chair=0, board=board0),
            PlayerState(chair=1, board=board1),
        ),
        hero_chair=player,
        dealer_chair=0,
        acting_chair=player,
        round_index=round_index,
        hero_incoming=incoming,
        hero_can_prepare=True,
        hero_can_confirm=True,
        action_required=True,
    )
    return enumerate_normal_actions(state)


@lru_cache(maxsize=None)
def _apply(
    board: PlayerBoard,
    action: NormalPlacementAction,
    incoming: tuple[Card, ...],
    round_index: int,
) -> PlayerBoard:
    updated, _ = apply_normal_action(
        board,
        action,
        round_index=round_index,
        incoming=incoming,
    )
    return updated


def _split_actions(
    first_player: int,
    first_action: NormalPlacementAction,
    second_action: NormalPlacementAction,
) -> tuple[NormalPlacementAction, NormalPlacementAction]:
    if first_player == 0:
        return first_action, second_action
    return second_action, first_action


class HUTwoRoundSubgame:
    """Reduced two-round HU OFC extensive-form benchmark with perfect recall.

    Pure state/action projections are memoized only by immutable canonical
    arguments. These caches change no chance support, infoset identity, legal
    action, utility or strategy semantics; they only remove repeated exact work.
    """

    exact_reference_value: float = 0.0

    def __init__(self) -> None:
        outcomes: list[TwoRoundChanceOutcome] = []
        for r3_0, r3_1, r4_0, r4_1, first in product(range(2), repeat=5):
            outcomes.append(
                TwoRoundChanceOutcome(
                    round3_hand0=ROUND3_HANDS[0][r3_0],
                    round3_hand1=ROUND3_HANDS[1][r3_1],
                    round4_hand0=ROUND4_HANDS[0][r4_0],
                    round4_hand1=ROUND4_HANDS[1][r4_1],
                    first_player=first,
                )
            )
        self.outcomes = tuple(outcomes)
        if len(self.outcomes) != 32:
            raise AssertionError("two-round reduced chance support must contain 32 outcomes")
        self.chance_probability = 1.0 / len(self.outcomes)
        self.info_actions = self._build_info_actions()

    def _register(
        self,
        target: dict[TwoRoundInfoSet, tuple[NormalPlacementAction, ...]],
        info: TwoRoundInfoSet,
        actions: tuple[NormalPlacementAction, ...],
    ) -> None:
        existing = target.get(info)
        if existing is None:
            target[info] = actions
        elif existing != actions:
            raise AssertionError("same infoset produced different legal action sets")

    @lru_cache(maxsize=None)
    def round3_first_info(self, outcome: TwoRoundChanceOutcome) -> TwoRoundInfoSet:
        player = outcome.first_player
        return TwoRoundInfoSet(
            player=player,
            round_index=3,
            role="first",
            own_round3_hand=_codes(outcome.hand(player, 3)),
        )

    @lru_cache(maxsize=None)
    def round3_second_info(
        self,
        outcome: TwoRoundChanceOutcome,
        first_action: NormalPlacementAction,
    ) -> TwoRoundInfoSet:
        player = outcome.second_player
        return TwoRoundInfoSet(
            player=player,
            round_index=3,
            role="second",
            own_round3_hand=_codes(outcome.hand(player, 3)),
            observed_current_first_public=action_public_key(first_action),
        )

    @lru_cache(maxsize=None)
    def round4_info(
        self,
        outcome: TwoRoundChanceOutcome,
        *,
        player: int,
        own_round3_action: NormalPlacementAction,
        opponent_round3_action: NormalPlacementAction,
        current_first_action: NormalPlacementAction | None,
    ) -> TwoRoundInfoSet:
        role = "first" if player == outcome.first_player else "second"
        return TwoRoundInfoSet(
            player=player,
            round_index=4,
            role=role,
            own_round3_hand=_codes(outcome.hand(player, 3)),
            observed_current_first_public=(
                None if current_first_action is None else action_public_key(current_first_action)
            ),
            own_round3_action=own_round3_action.key(),
            opponent_round3_public=action_public_key(opponent_round3_action),
            own_round4_hand=_codes(outcome.hand(player, 4)),
        )

    @lru_cache(maxsize=None)
    def _round3_actions(
        self,
        outcome: TwoRoundChanceOutcome,
        player: int,
    ) -> tuple[NormalPlacementAction, ...]:
        return _actions_for(
            player,
            BASE_BOARDS[0],
            BASE_BOARDS[1],
            outcome.hand(player, 3),
            3,
        )

    @lru_cache(maxsize=None)
    def _boards_after_round3(
        self,
        outcome: TwoRoundChanceOutcome,
        first_action: NormalPlacementAction,
        second_action: NormalPlacementAction,
    ) -> tuple[PlayerBoard, PlayerBoard, NormalPlacementAction, NormalPlacementAction]:
        action0, action1 = _split_actions(outcome.first_player, first_action, second_action)
        board0 = _apply(BASE_BOARDS[0], action0, outcome.round3_hand0, 3)
        board1 = _apply(BASE_BOARDS[1], action1, outcome.round3_hand1, 3)
        return board0, board1, action0, action1

    @lru_cache(maxsize=None)
    def _round4_actions(
        self,
        outcome: TwoRoundChanceOutcome,
        player: int,
        board0: PlayerBoard,
        board1: PlayerBoard,
    ) -> tuple[NormalPlacementAction, ...]:
        return _actions_for(
            player,
            board0,
            board1,
            outcome.hand(player, 4),
            4,
        )

    def _build_info_actions(self) -> dict[TwoRoundInfoSet, tuple[NormalPlacementAction, ...]]:
        info_actions: dict[TwoRoundInfoSet, tuple[NormalPlacementAction, ...]] = {}
        for outcome in self.outcomes:
            first = outcome.first_player
            second = outcome.second_player
            first_r3_actions = self._round3_actions(outcome, first)
            self._register(info_actions, self.round3_first_info(outcome), first_r3_actions)
            second_r3_actions = self._round3_actions(outcome, second)

            for first_r3 in first_r3_actions:
                second_r3_info = self.round3_second_info(outcome, first_r3)
                self._register(info_actions, second_r3_info, second_r3_actions)
                for second_r3 in second_r3_actions:
                    board0, board1, action0_r3, action1_r3 = self._boards_after_round3(
                        outcome, first_r3, second_r3
                    )
                    first_own_r3 = action0_r3 if first == 0 else action1_r3
                    first_opp_r3 = action1_r3 if first == 0 else action0_r3
                    second_own_r3 = action0_r3 if second == 0 else action1_r3
                    second_opp_r3 = action1_r3 if second == 0 else action0_r3

                    first_r4_info = self.round4_info(
                        outcome,
                        player=first,
                        own_round3_action=first_own_r3,
                        opponent_round3_action=first_opp_r3,
                        current_first_action=None,
                    )
                    first_r4_actions = self._round4_actions(
                        outcome, first, board0, board1
                    )
                    self._register(info_actions, first_r4_info, first_r4_actions)

                    second_r4_actions = self._round4_actions(
                        outcome, second, board0, board1
                    )
                    for first_r4 in first_r4_actions:
                        second_r4_info = self.round4_info(
                            outcome,
                            player=second,
                            own_round3_action=second_own_r3,
                            opponent_round3_action=second_opp_r3,
                            current_first_action=first_r4,
                        )
                        self._register(info_actions, second_r4_info, second_r4_actions)
        return info_actions

    def actions(self, info: TwoRoundInfoSet) -> tuple[NormalPlacementAction, ...]:
        return self.info_actions[info]

    def _distribution(
        self,
        profile: StrategyProfile,
        info: TwoRoundInfoSet,
    ) -> dict[NormalPlacementAction, float]:
        legal = self.actions(info)
        supplied = profile.get(info)
        if supplied is None:
            probability = 1.0 / len(legal)
            return {action: probability for action in legal}
        illegal = set(supplied) - set(legal)
        if illegal:
            raise ValueError("strategy contains illegal actions")
        values = {action: float(supplied.get(action, 0.0)) for action in legal}
        if any(value < 0.0 for value in values.values()):
            raise ValueError("strategy probabilities cannot be negative")
        total = sum(values.values())
        if total <= 0.0:
            raise ValueError("strategy probabilities need positive mass")
        return {action: value / total for action, value in values.items()}

    def uniform_profile(self) -> dict[TwoRoundInfoSet, dict[NormalPlacementAction, float]]:
        return {
            info: {action: 1.0 / len(actions) for action in actions}
            for info, actions in self.info_actions.items()
        }

    @lru_cache(maxsize=None)
    def terminal_u0(
        self,
        outcome: TwoRoundChanceOutcome,
        first_r3: NormalPlacementAction,
        second_r3: NormalPlacementAction,
        first_r4: NormalPlacementAction,
        second_r4: NormalPlacementAction,
    ) -> int:
        board0, board1, _, _ = self._boards_after_round3(
            outcome, first_r3, second_r3
        )
        action0_r4, action1_r4 = _split_actions(
            outcome.first_player, first_r4, second_r4
        )
        board0 = _apply(board0, action0_r4, outcome.round4_hand0, 4)
        board1 = _apply(board1, action1_r4, outcome.round4_hand1, 4)
        if not board0.is_complete() or not board1.is_complete():
            raise AssertionError("two-round terminal did not complete both boards")
        return settle_raw_points((board0, board1)).points_by_chair[0]

    def terminal_count(self) -> int:
        total = 0
        for outcome in self.outcomes:
            first = outcome.first_player
            second = outcome.second_player
            first_r3_actions = self._round3_actions(outcome, first)
            second_r3_actions = self._round3_actions(outcome, second)
            for first_r3 in first_r3_actions:
                for second_r3 in second_r3_actions:
                    board0, board1, _, _ = self._boards_after_round3(
                        outcome, first_r3, second_r3
                    )
                    total += len(self._round4_actions(outcome, first, board0, board1)) * len(
                        self._round4_actions(outcome, second, board0, board1)
                    )
        return total

    def expected_u0(self, profile: StrategyProfile) -> float:
        total = 0.0
        cp = self.chance_probability
        for outcome in self.outcomes:
            first = outcome.first_player
            second = outcome.second_player
            first_r3_info = self.round3_first_info(outcome)
            first_r3_dist = self._distribution(profile, first_r3_info)
            for first_r3, p_first_r3 in first_r3_dist.items():
                second_r3_info = self.round3_second_info(outcome, first_r3)
                second_r3_dist = self._distribution(profile, second_r3_info)
                for second_r3, p_second_r3 in second_r3_dist.items():
                    board0, board1, action0_r3, action1_r3 = self._boards_after_round3(
                        outcome, first_r3, second_r3
                    )
                    first_own_r3 = action0_r3 if first == 0 else action1_r3
                    first_opp_r3 = action1_r3 if first == 0 else action0_r3
                    second_own_r3 = action0_r3 if second == 0 else action1_r3
                    second_opp_r3 = action1_r3 if second == 0 else action0_r3

                    first_r4_info = self.round4_info(
                        outcome,
                        player=first,
                        own_round3_action=first_own_r3,
                        opponent_round3_action=first_opp_r3,
                        current_first_action=None,
                    )
                    first_r4_dist = self._distribution(profile, first_r4_info)
                    for first_r4, p_first_r4 in first_r4_dist.items():
                        second_r4_info = self.round4_info(
                            outcome,
                            player=second,
                            own_round3_action=second_own_r3,
                            opponent_round3_action=second_opp_r3,
                            current_first_action=first_r4,
                        )
                        second_r4_dist = self._distribution(profile, second_r4_info)
                        for second_r4, p_second_r4 in second_r4_dist.items():
                            total += (
                                cp
                                * p_first_r3
                                * p_second_r3
                                * p_first_r4
                                * p_second_r4
                                * self.terminal_u0(
                                    outcome,
                                    first_r3,
                                    second_r3,
                                    first_r4,
                                    second_r4,
                                )
                            )
        return total

    def count_merged_round4_infosets(self) -> int:
        histories: dict[TwoRoundInfoSet, set[TwoRoundChanceOutcome]] = {}
        for outcome in self.outcomes:
            first = outcome.first_player
            second = outcome.second_player
            for first_r3 in self._round3_actions(outcome, first):
                for second_r3 in self._round3_actions(outcome, second):
                    board0, board1, action0_r3, action1_r3 = self._boards_after_round3(
                        outcome, first_r3, second_r3
                    )
                    for player in (first, second):
                        own = action0_r3 if player == 0 else action1_r3
                        opp = action1_r3 if player == 0 else action0_r3
                        if player == first:
                            info = self.round4_info(
                                outcome,
                                player=player,
                                own_round3_action=own,
                                opponent_round3_action=opp,
                                current_first_action=None,
                            )
                            histories.setdefault(info, set()).add(outcome)
                        else:
                            for first_r4 in self._round4_actions(
                                outcome, first, board0, board1
                            ):
                                info = self.round4_info(
                                    outcome,
                                    player=player,
                                    own_round3_action=own,
                                    opponent_round3_action=opp,
                                    current_first_action=first_r4,
                                )
                                histories.setdefault(info, set()).add(outcome)
        return sum(1 for outcomes in histories.values() if len(outcomes) > 1)

    def assert_terminal_swap_symmetry(self) -> int:
        support = set(self.outcomes)
        checks = 0
        for outcome in self.outcomes:
            mirrored = outcome.mirrored_swapped()
            if mirrored not in support:
                raise AssertionError("mirrored-swapped two-round outcome missing")
            first = outcome.first_player
            second = outcome.second_player
            for first_r3 in self._round3_actions(outcome, first):
                for second_r3 in self._round3_actions(outcome, second):
                    board0, board1, _, _ = self._boards_after_round3(
                        outcome, first_r3, second_r3
                    )
                    for first_r4 in self._round4_actions(outcome, first, board0, board1):
                        for second_r4 in self._round4_actions(outcome, second, board0, board1):
                            u0 = self.terminal_u0(
                                outcome, first_r3, second_r3, first_r4, second_r4
                            )
                            mirror_u0 = self.terminal_u0(
                                mirrored,
                                mirror_action(first_r3),
                                mirror_action(second_r3),
                                mirror_action(first_r4),
                                mirror_action(second_r4),
                            )
                            if u0 != -mirror_u0:
                                raise AssertionError(
                                    "two-round terminal symmetry failed: "
                                    f"u0={u0} mirror={mirror_u0}"
                                )
                            checks += 1
        return checks
