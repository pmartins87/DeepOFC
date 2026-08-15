from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Mapping

from .hu_subgame import (
    HUChanceOutcome,
    HUFinalRoundSubgame,
    HUInfoSet,
    HUPlacementAction,
    StrategyProfile,
)


@dataclass(frozen=True)
class MCCFRSnapshot:
    iteration: int
    expected_u0: float
    br0: float
    br1: float
    nash_conv: float
    exploitability: float


class ExternalSamplingMCCFR:
    """External-sampling MCCFR specialized to the reduced HU OFC subgame.

    One global iteration performs one traversal for each player. Chance and the
    non-traversing player's actions are sampled; every action of the traverser
    is enumerated at the traverser's reached information set.

    Strategy averaging is exact for this reduced game. Because each player acts
    at most once, player-own reach before every information set is 1. A lazy
    time-integration scheme records the time-average strategy actually USED by
    each completed iteration without iterating over every untouched information
    set on every sampled traversal.
    """

    def __init__(self, game: HUFinalRoundSubgame, *, seed: int = 1) -> None:
        self.game = game
        self.rng = random.Random(seed)
        self.iteration = 0
        self.regrets = {
            info: {action: 0.0 for action in actions}
            for info, actions in game.info_actions.items()
        }
        self.strategy_sum = {
            info: {action: 0.0 for action in actions}
            for info, actions in game.info_actions.items()
        }
        # First iteration in which the currently implied regret-matching strategy
        # is USED. The initial uniform strategy is active from iteration 1.
        self.active_since = {info: 1 for info in game.info_actions}

    def _distribution(self, info: HUInfoSet) -> dict[HUPlacementAction, float]:
        regrets = self.regrets[info]
        positive = {action: max(0.0, regret) for action, regret in regrets.items()}
        total = sum(positive.values())
        if total <= 0.0:
            probability = 1.0 / len(positive)
            return {action: probability for action in positive}
        return {action: value / total for action, value in positive.items()}

    def _sample_action(
        self,
        distribution: Mapping[HUPlacementAction, float],
    ) -> HUPlacementAction:
        threshold = self.rng.random()
        cumulative = 0.0
        last: HUPlacementAction | None = None
        for action in sorted(distribution):
            last = action
            cumulative += distribution[action]
            if threshold <= cumulative:
                return action
        if last is None:
            raise RuntimeError("cannot sample empty action distribution")
        return last

    def _terminal_own(
        self,
        outcome: HUChanceOutcome,
        first_action: HUPlacementAction,
        second_action: HUPlacementAction,
        traverser: int,
    ) -> float:
        u0 = float(self.game.terminal_u0(outcome, first_action, second_action))
        return u0 if traverser == 0 else -u0

    def _traverse_second(
        self,
        outcome: HUChanceOutcome,
        first_action: HUPlacementAction,
        traverser: int,
        delta: dict[HUInfoSet, dict[HUPlacementAction, float]],
    ) -> float:
        second = outcome.second_player
        info = self.game.second_info(outcome, first_action)
        strategy = self._distribution(info)
        if second != traverser:
            sampled = self._sample_action(strategy)
            return self._terminal_own(outcome, first_action, sampled, traverser)

        action_values: dict[HUPlacementAction, float] = {}
        node_value = 0.0
        for action, probability in strategy.items():
            value = self._terminal_own(outcome, first_action, action, traverser)
            action_values[action] = value
            node_value += probability * value
        bucket = delta.setdefault(
            info, {action: 0.0 for action in self.game.actions(info)}
        )
        for action, value in action_values.items():
            bucket[action] += value - node_value
        return node_value

    def _sampled_traversal(
        self,
        traverser: int,
        delta: dict[HUInfoSet, dict[HUPlacementAction, float]],
    ) -> None:
        outcome = self.game.outcomes[self.rng.randrange(len(self.game.outcomes))]
        first = outcome.first_player
        info = self.game.first_info(outcome)
        strategy = self._distribution(info)

        if first != traverser:
            sampled = self._sample_action(strategy)
            self._traverse_second(outcome, sampled, traverser, delta)
            return

        action_values: dict[HUPlacementAction, float] = {}
        node_value = 0.0
        for action, probability in strategy.items():
            value = self._traverse_second(outcome, action, traverser, delta)
            action_values[action] = value
            node_value += probability * value
        bucket = delta.setdefault(
            info, {action: 0.0 for action in self.game.actions(info)}
        )
        for action, value in action_values.items():
            bucket[action] += value - node_value

    def _flush_strategy_used_through_iteration(self, info: HUInfoSet, t: int) -> None:
        # The current strategy was used in every iteration active_since..t,
        # inclusive. Flush that exact pre-update interval before regrets change.
        count = t - self.active_since[info] + 1
        if count <= 0:
            return
        strategy = self._distribution(info)
        for action, probability in strategy.items():
            self.strategy_sum[info][action] += count * probability

    def step(self) -> None:
        t = self.iteration + 1
        delta: dict[HUInfoSet, dict[HUPlacementAction, float]] = {}
        # Both traversals see the same pre-iteration regret tables because all
        # updates are aggregated and applied only after both traversers finish.
        self._sampled_traversal(0, delta)
        self._sampled_traversal(1, delta)

        for info, action_delta in delta.items():
            # Iteration t has already used the old strategy. Credit it before
            # applying the regret update; the new strategy starts at t+1.
            self._flush_strategy_used_through_iteration(info, t)
            for action, increment in action_delta.items():
                self.regrets[info][action] += increment
            self.active_since[info] = t + 1
        self.iteration = t

    def run(self, iterations: int) -> None:
        if iterations < 0:
            raise ValueError("iterations must be non-negative")
        for _ in range(iterations):
            self.step()

    def current_profile(self) -> dict[HUInfoSet, dict[HUPlacementAction, float]]:
        return {info: self._distribution(info) for info in self.game.info_actions}

    def average_profile(self) -> dict[HUInfoSet, dict[HUPlacementAction, float]]:
        if self.iteration == 0:
            return self.game.uniform_profile()
        profile: dict[HUInfoSet, dict[HUPlacementAction, float]] = {}
        for info, actions in self.game.info_actions.items():
            totals = dict(self.strategy_sum[info])
            # Any strategy not yet flushed has been used from active_since
            # through the latest completed iteration, inclusive.
            count = self.iteration - self.active_since[info] + 1
            if count > 0:
                current = self._distribution(info)
                for action, probability in current.items():
                    totals[action] += count * probability
            mass = sum(totals.values())
            if mass <= 0.0:
                probability = 1.0 / len(actions)
                profile[info] = {action: probability for action in actions}
            else:
                profile[info] = {action: totals[action] / mass for action in actions}
        return profile

    def snapshot(self) -> MCCFRSnapshot:
        profile: StrategyProfile = self.average_profile()
        expected = self.game.expected_u0(profile)
        br0 = self.game.best_response_value(profile, 0)
        br1 = self.game.best_response_value(profile, 1)
        nash_conv = br0 + br1
        return MCCFRSnapshot(
            iteration=self.iteration,
            expected_u0=expected,
            br0=br0,
            br1=br1,
            nash_conv=nash_conv,
            exploitability=0.5 * nash_conv,
        )
