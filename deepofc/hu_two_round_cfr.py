from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Literal

from .actions import NormalPlacementAction
from .hu_two_round import HUTwoRoundSubgame, TwoRoundInfoSet
from .hu_two_round_br import exact_nash_conv


CFRVariant = Literal["cfr_plus", "dcfr"]


@dataclass(frozen=True)
class TwoRoundCFRSnapshot:
    iteration: int
    expected_u0: float
    br0: float
    br1: float
    nash_conv: float
    exploitability: float


class TwoRoundFullTreeCFR:
    """Deterministic simultaneous-update CFR-family solver for HUTwoRoundSubgame.

    Unlike the first one-decision R6 benchmark, each player acts twice here.
    Counterfactual regret weights therefore explicitly exclude the acting
    player's own earlier reach while retaining chance and opponent reach.
    Average-strategy weights use the player's own sequence reach.
    """

    def __init__(
        self,
        game: HUTwoRoundSubgame,
        *,
        variant: CFRVariant = "dcfr",
        dcfr_alpha: float = 1.5,
        dcfr_beta: float = 0.0,
        dcfr_gamma: float = 2.0,
    ) -> None:
        if variant not in {"cfr_plus", "dcfr"}:
            raise ValueError(f"unsupported variant: {variant}")
        self.game = game
        self.variant = variant
        self.dcfr_alpha = float(dcfr_alpha)
        self.dcfr_beta = float(dcfr_beta)
        self.dcfr_gamma = float(dcfr_gamma)
        self.iteration = 0
        self.regrets = {
            info: {action: 0.0 for action in actions}
            for info, actions in game.info_actions.items()
        }
        self.strategy_sum = {
            info: {action: 0.0 for action in actions}
            for info, actions in game.info_actions.items()
        }

    def _distribution(
        self,
        info: TwoRoundInfoSet,
    ) -> dict[NormalPlacementAction, float]:
        values = self.regrets[info]
        positive = {action: max(0.0, regret) for action, regret in values.items()}
        total = sum(positive.values())
        if total <= 0.0:
            probability = 1.0 / len(positive)
            return {action: probability for action in positive}
        return {action: value / total for action, value in positive.items()}

    def current_profile(self):
        return {info: self._distribution(info) for info in self.game.info_actions}

    def average_profile(self):
        profile = {}
        for info, totals in self.strategy_sum.items():
            mass = sum(totals.values())
            if mass <= 0.0:
                probability = 1.0 / len(totals)
                profile[info] = {action: probability for action in totals}
            else:
                profile[info] = {action: value / mass for action, value in totals.items()}
        return profile

    @staticmethod
    def _own_regret(
        actor: int,
        action_u0: float,
        node_u0: float,
    ) -> float:
        return (
            action_u0 - node_u0
            if actor == 0
            else node_u0 - action_u0
        )

    @staticmethod
    def _add_strategy(
        target: dict,
        info: TwoRoundInfoSet,
        distribution: dict[NormalPlacementAction, float],
        reach_weight: float,
    ) -> None:
        bucket = target.setdefault(
            info, {action: 0.0 for action in distribution}
        )
        for action, probability in distribution.items():
            bucket[action] += reach_weight * probability

    @staticmethod
    def _add_regret(
        target: dict,
        info: TwoRoundInfoSet,
        action_values: dict[NormalPlacementAction, float],
        node_value: float,
        actor: int,
        cf_weight: float,
    ) -> None:
        bucket = target.setdefault(
            info, {action: 0.0 for action in action_values}
        )
        for action, value in action_values.items():
            bucket[action] += cf_weight * TwoRoundFullTreeCFR._own_regret(
                actor, value, node_value
            )

    def step(self) -> None:
        t = self.iteration + 1
        cp = self.game.chance_probability
        current = {
            info: self._distribution(info)
            for info in self.game.info_actions
        }
        regret_delta: dict = {}
        average_delta: dict = {}

        for outcome in self.game.outcomes:
            first = outcome.first_player
            second = outcome.second_player

            first_r3_info = self.game.round3_first_info(outcome)
            first_r3_dist = current[first_r3_info]
            self._add_strategy(
                average_delta, first_r3_info, first_r3_dist, cp
            )
            first_r3_action_values: dict[NormalPlacementAction, float] = {}

            for first_r3, p_first_r3 in first_r3_dist.items():
                second_r3_info = self.game.round3_second_info(outcome, first_r3)
                second_r3_dist = current[second_r3_info]
                self._add_strategy(
                    average_delta, second_r3_info, second_r3_dist, cp
                )
                second_r3_action_values: dict[NormalPlacementAction, float] = {}

                for second_r3, p_second_r3 in second_r3_dist.items():
                    board0, board1, action0_r3, action1_r3 = self.game._boards_after_round3(
                        outcome, first_r3, second_r3
                    )
                    first_own_r3 = action0_r3 if first == 0 else action1_r3
                    first_opp_r3 = action1_r3 if first == 0 else action0_r3
                    second_own_r3 = action0_r3 if second == 0 else action1_r3
                    second_opp_r3 = action1_r3 if second == 0 else action0_r3

                    first_r4_info = self.game.round4_info(
                        outcome,
                        player=first,
                        own_round3_action=first_own_r3,
                        opponent_round3_action=first_opp_r3,
                        current_first_action=None,
                    )
                    first_r4_dist = current[first_r4_info]
                    self._add_strategy(
                        average_delta,
                        first_r4_info,
                        first_r4_dist,
                        cp * p_first_r3,
                    )
                    first_r4_action_values: dict[NormalPlacementAction, float] = {}

                    for first_r4, p_first_r4 in first_r4_dist.items():
                        second_r4_info = self.game.round4_info(
                            outcome,
                            player=second,
                            own_round3_action=second_own_r3,
                            opponent_round3_action=second_opp_r3,
                            current_first_action=first_r4,
                        )
                        second_r4_dist = current[second_r4_info]
                        self._add_strategy(
                            average_delta,
                            second_r4_info,
                            second_r4_dist,
                            cp * p_second_r3,
                        )

                        second_r4_action_values = {
                            second_r4: float(
                                self.game.terminal_u0(
                                    outcome,
                                    first_r3,
                                    second_r3,
                                    first_r4,
                                    second_r4,
                                )
                            )
                            for second_r4 in second_r4_dist
                        }
                        second_r4_node = sum(
                            second_r4_dist[action] * value
                            for action, value in second_r4_action_values.items()
                        )
                        self._add_regret(
                            regret_delta,
                            second_r4_info,
                            second_r4_action_values,
                            second_r4_node,
                            second,
                            cp * p_first_r3 * p_first_r4,
                        )
                        first_r4_action_values[first_r4] = second_r4_node

                    first_r4_node = sum(
                        first_r4_dist[action] * value
                        for action, value in first_r4_action_values.items()
                    )
                    self._add_regret(
                        regret_delta,
                        first_r4_info,
                        first_r4_action_values,
                        first_r4_node,
                        first,
                        cp * p_second_r3,
                    )
                    second_r3_action_values[second_r3] = first_r4_node

                second_r3_node = sum(
                    second_r3_dist[action] * value
                    for action, value in second_r3_action_values.items()
                )
                self._add_regret(
                    regret_delta,
                    second_r3_info,
                    second_r3_action_values,
                    second_r3_node,
                    second,
                    cp * p_first_r3,
                )
                first_r3_action_values[first_r3] = second_r3_node

            first_r3_node = sum(
                first_r3_dist[action] * value
                for action, value in first_r3_action_values.items()
            )
            self._add_regret(
                regret_delta,
                first_r3_info,
                first_r3_action_values,
                first_r3_node,
                first,
                cp,
            )

        if self.variant == "dcfr":
            pos_power = float(t) ** self.dcfr_alpha
            neg_power = float(t) ** self.dcfr_beta
            pos_factor = pos_power / (pos_power + 1.0)
            neg_factor = neg_power / (neg_power + 1.0)
            for values in self.regrets.values():
                for action, old in tuple(values.items()):
                    values[action] = old * (
                        pos_factor if old >= 0.0 else neg_factor
                    )

        for info, delta in regret_delta.items():
            values = self.regrets[info]
            for action, increment in delta.items():
                updated = values[action] + increment
                if self.variant == "cfr_plus":
                    updated = max(0.0, updated)
                if not isfinite(updated):
                    raise FloatingPointError("non-finite two-round regret")
                values[action] = updated

        average_weight = (
            float(t)
            if self.variant == "cfr_plus"
            else float(t) ** self.dcfr_gamma
        )
        for info, delta in average_delta.items():
            totals = self.strategy_sum[info]
            for action, increment in delta.items():
                totals[action] += average_weight * increment

        self.iteration = t

    def run(self, iterations: int) -> None:
        if iterations < 0:
            raise ValueError("iterations must be non-negative")
        for _ in range(iterations):
            self.step()

    def snapshot(self) -> TwoRoundCFRSnapshot:
        profile = self.average_profile()
        expected = self.game.expected_u0(profile)
        nash_conv, br0, br1 = exact_nash_conv(self.game, profile)
        return TwoRoundCFRSnapshot(
            iteration=self.iteration,
            expected_u0=expected,
            br0=br0.value,
            br1=br1.value,
            nash_conv=nash_conv,
            exploitability=0.5 * nash_conv,
        )
