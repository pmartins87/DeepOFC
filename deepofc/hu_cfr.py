from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Literal

from .hu_subgame import (
    HUFinalRoundSubgame,
    HUInfoSet,
    HUPlacementAction,
    StrategyProfile,
)


CFRVariant = Literal["cfr", "cfr_plus", "dcfr"]


@dataclass(frozen=True)
class CFRSnapshot:
    iteration: int
    expected_u0: float
    br0: float
    br1: float
    nash_conv: float
    exploitability: float


class FullTreeCFR:
    """Deterministic full-tree CFR-family reference for the reduced HU game.

    This is deliberately specialized to HUFinalRoundSubgame. Every player acts
    exactly once, so average-strategy reach weighting is particularly simple;
    regrets are still accumulated with exact counterfactual opponent/chance
    reach over every hidden physical history.

    The implementation keeps all regret updates for an iteration in a separate
    delta table. That is important for CFR+: clipping per history rather than
    after the full information-set counterfactual sum would change the algorithm.
    """

    def __init__(
        self,
        game: HUFinalRoundSubgame,
        *,
        variant: CFRVariant = "cfr_plus",
        dcfr_alpha: float = 1.5,
        dcfr_beta: float = 0.0,
        dcfr_gamma: float = 2.0,
    ) -> None:
        if variant not in {"cfr", "cfr_plus", "dcfr"}:
            raise ValueError(f"unsupported CFR variant: {variant}")
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

    def _current_distribution(self, info: HUInfoSet) -> dict[HUPlacementAction, float]:
        regrets = self.regrets[info]
        positive = {action: max(0.0, regret) for action, regret in regrets.items()}
        total = sum(positive.values())
        if total <= 0.0:
            probability = 1.0 / len(positive)
            return {action: probability for action in positive}
        return {action: value / total for action, value in positive.items()}

    def current_profile(self) -> dict[HUInfoSet, dict[HUPlacementAction, float]]:
        return {info: self._current_distribution(info) for info in self.regrets}

    def average_profile(self) -> dict[HUInfoSet, dict[HUPlacementAction, float]]:
        profile: dict[HUInfoSet, dict[HUPlacementAction, float]] = {}
        for info, totals in self.strategy_sum.items():
            mass = sum(totals.values())
            if mass <= 0.0:
                probability = 1.0 / len(totals)
                profile[info] = {action: probability for action in totals}
            else:
                profile[info] = {action: value / mass for action, value in totals.items()}
        return profile

    def _average_iteration_weight(self, iteration: int) -> float:
        if self.variant == "cfr_plus":
            # Linear CFR+ averaging. No arbitrary warm-up delay is hidden here;
            # benchmark scripts may compare checkpoints directly from iteration 1.
            return float(iteration)
        if self.variant == "dcfr":
            return float(iteration) ** self.dcfr_gamma
        return 1.0

    def step(self) -> None:
        t = self.iteration + 1
        cp = self.game.chance_probability
        current = {
            info: self._current_distribution(info)
            for info in self.regrets
        }
        regret_delta = {
            info: {action: 0.0 for action in actions}
            for info, actions in self.game.info_actions.items()
        }
        average_delta = {
            info: {action: 0.0 for action in actions}
            for info, actions in self.game.info_actions.items()
        }

        for outcome in self.game.outcomes:
            first_player = outcome.first_player
            second_player = outcome.second_player
            first_info = self.game.first_info(outcome)
            first_dist = current[first_info]

            # Average strategy reach excludes opponent reach. In this reduced
            # game neither player has an earlier own action, so structural chance
            # mass is the only history weight needed at each infoset.
            for action, probability in first_dist.items():
                average_delta[first_info][action] += cp * probability

            first_action_u0: dict[HUPlacementAction, float] = {}
            for first_action, p_first in first_dist.items():
                second_info = self.game.second_info(outcome, first_action)
                second_dist = current[second_info]
                for action, probability in second_dist.items():
                    # Deliberately exclude p_first: that is opponent reach for the
                    # second player and does not belong in average-strategy reach.
                    average_delta[second_info][action] += cp * probability

                u0_by_second: dict[HUPlacementAction, float] = {}
                u0_after_first = 0.0
                for second_action, p_second in second_dist.items():
                    u0 = float(
                        self.game.terminal_u0(outcome, first_action, second_action)
                    )
                    u0_by_second[second_action] = u0
                    u0_after_first += p_second * u0
                first_action_u0[first_action] = u0_after_first

                # Exact counterfactual regret for the second actor. Opponent's
                # first-action reach is included; second player's own strategy is
                # excluded from the counterfactual reach multiplier.
                for second_action, u0 in u0_by_second.items():
                    if second_player == 0:
                        action_regret = u0 - u0_after_first
                    else:
                        action_regret = u0_after_first - u0
                    regret_delta[second_info][second_action] += (
                        cp * p_first * action_regret
                    )

            u0_at_first = sum(
                first_dist[action] * value
                for action, value in first_action_u0.items()
            )
            for first_action, u0 in first_action_u0.items():
                if first_player == 0:
                    action_regret = u0 - u0_at_first
                else:
                    action_regret = u0_at_first - u0
                # No opponent action precedes the first actor.
                regret_delta[first_info][first_action] += cp * action_regret

        if self.variant == "dcfr":
            pos_power = float(t) ** self.dcfr_alpha
            neg_power = float(t) ** self.dcfr_beta
            pos_factor = pos_power / (pos_power + 1.0)
            neg_factor = neg_power / (neg_power + 1.0)
            for info, values in self.regrets.items():
                for action, old in tuple(values.items()):
                    values[action] = old * (pos_factor if old >= 0.0 else neg_factor)

        for info, values in self.regrets.items():
            for action in values:
                updated = values[action] + regret_delta[info][action]
                if self.variant == "cfr_plus":
                    updated = max(0.0, updated)
                if not isfinite(updated):
                    raise FloatingPointError("non-finite cumulative regret")
                values[action] = updated

        average_weight = self._average_iteration_weight(t)
        for info, values in self.strategy_sum.items():
            for action in values:
                increment = average_weight * average_delta[info][action]
                if not isfinite(increment):
                    raise FloatingPointError("non-finite average-strategy increment")
                values[action] += increment

        self.iteration = t

    def run(self, iterations: int) -> None:
        if iterations < 0:
            raise ValueError("iterations must be non-negative")
        for _ in range(iterations):
            self.step()

    def snapshot(self, *, average: bool = True) -> CFRSnapshot:
        profile: StrategyProfile = self.average_profile() if average else self.current_profile()
        expected = self.game.expected_u0(profile)
        br0 = self.game.best_response_value(profile, 0)
        br1 = self.game.best_response_value(profile, 1)
        nash_conv = br0 + br1
        return CFRSnapshot(
            iteration=self.iteration,
            expected_u0=expected,
            br0=br0,
            br1=br1,
            nash_conv=nash_conv,
            exploitability=0.5 * nash_conv,
        )
