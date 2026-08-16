from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from .actions import NormalPlacementAction
from .hu_three_round_sequential import HUThreeRoundSequentialSubgame
from .sequential import HUPlayerObservation, HUSequentialNormalState


@dataclass(frozen=True)
class ThreeRoundFullTreeStats:
    iterations: int
    terminal_evaluations: int
    infosets: int


class HUThreeRoundFullTreeDCFR:
    """Recursive simultaneous full-tree DCFR on the canonical sequential game.

    Counterfactual regret at a player-i infoset is weighted by chance and the
    opponent sequence reach only. Average strategy is weighted by chance and
    player i's own sequence reach. Regrets are discounted before the new
    iteration's exact regret delta is committed, matching the already certified
    two-round DCFR ordering.

    Derived states are expanded through ``game.transition``. Sequential games
    implement that transition with their validated fast path, avoiding repeated
    full-state invariant scans at every node while preserving the same legal
    action and terminal semantics.
    """

    def __init__(
        self,
        game: HUThreeRoundSequentialSubgame,
        *,
        alpha: float = 1.5,
        beta: float = 0.0,
        gamma: float = 2.0,
    ) -> None:
        self.game = game
        self.alpha = float(alpha)
        self.beta = float(beta)
        self.gamma = float(gamma)
        self.iteration = 0
        self.terminal_evaluations = 0
        self.regrets: dict[
            HUPlayerObservation, dict[NormalPlacementAction, float]
        ] = {}
        self.strategy_sum: dict[
            HUPlayerObservation, dict[NormalPlacementAction, float]
        ] = {}

    def _ensure_info(self, info: HUPlayerObservation):
        actions = self.game.actions(info)
        regrets = self.regrets.get(info)
        if regrets is None:
            regrets = {action: 0.0 for action in actions}
            self.regrets[info] = regrets
            self.strategy_sum[info] = {action: 0.0 for action in actions}
        return regrets

    def _distribution(self, info: HUPlayerObservation):
        regrets = self._ensure_info(info)
        positive = {action: max(0.0, value) for action, value in regrets.items()}
        total = sum(positive.values())
        if total <= 0.0:
            p = 1.0 / len(positive)
            return {action: p for action in positive}
        return {action: value / total for action, value in positive.items()}

    def current_profile(self):
        return {info: self._distribution(info) for info in tuple(self.regrets)}

    def average_profile(self):
        profile = {}
        for info, totals in self.strategy_sum.items():
            mass = sum(totals.values())
            if mass <= 0.0:
                p = 1.0 / len(totals)
                profile[info] = {action: p for action in totals}
            else:
                profile[info] = {
                    action: value / mass for action, value in totals.items()
                }
        return profile

    @staticmethod
    def _own_regret(actor: int, action_u0: float, node_u0: float) -> float:
        return action_u0 - node_u0 if actor == 0 else node_u0 - action_u0

    def _traverse(
        self,
        state: HUSequentialNormalState,
        *,
        chance_reach: float,
        reach0: float,
        reach1: float,
        regret_delta: dict,
        average_delta: dict,
    ) -> float:
        if state.terminal:
            self.terminal_evaluations += 1
            return float(self.game.terminal_u0(state))

        info = self.game.info(state)
        actor = state.acting_chair
        strategy = self._distribution(info)
        own_reach = reach0 if actor == 0 else reach1
        opponent_reach = reach1 if actor == 0 else reach0

        avg_bucket = average_delta.setdefault(
            info, {action: 0.0 for action in strategy}
        )
        avg_weight = chance_reach * own_reach
        for action, probability in strategy.items():
            avg_bucket[action] += avg_weight * probability

        action_values = {}
        node_u0 = 0.0
        for action, probability in strategy.items():
            child_state = self.game.transition(state, action)
            if actor == 0:
                child = self._traverse(
                    child_state,
                    chance_reach=chance_reach,
                    reach0=reach0 * probability,
                    reach1=reach1,
                    regret_delta=regret_delta,
                    average_delta=average_delta,
                )
            else:
                child = self._traverse(
                    child_state,
                    chance_reach=chance_reach,
                    reach0=reach0,
                    reach1=reach1 * probability,
                    regret_delta=regret_delta,
                    average_delta=average_delta,
                )
            action_values[action] = child
            node_u0 += probability * child

        regret_bucket = regret_delta.setdefault(
            info, {action: 0.0 for action in strategy}
        )
        cf_weight = chance_reach * opponent_reach
        for action, value in action_values.items():
            regret_bucket[action] += cf_weight * self._own_regret(
                actor, value, node_u0
            )
        return node_u0

    def step(self) -> None:
        t = self.iteration + 1
        regret_delta = {}
        average_delta = {}
        for outcome in self.game.outcomes:
            self._traverse(
                self.game.initial_state(outcome),
                chance_reach=self.game.chance_probability,
                reach0=1.0,
                reach1=1.0,
                regret_delta=regret_delta,
                average_delta=average_delta,
            )

        pos_power = float(t) ** self.alpha
        neg_power = float(t) ** self.beta
        pos_factor = pos_power / (pos_power + 1.0)
        neg_factor = neg_power / (neg_power + 1.0)
        for values in self.regrets.values():
            for action, old in tuple(values.items()):
                values[action] = old * (pos_factor if old >= 0.0 else neg_factor)

        for info, increments in regret_delta.items():
            values = self.regrets[info]
            for action, increment in increments.items():
                updated = values[action] + increment
                if not isfinite(updated):
                    raise FloatingPointError("non-finite three-round DCFR regret")
                values[action] = updated

        temporal_weight = float(t) ** self.gamma
        for info, increments in average_delta.items():
            totals = self.strategy_sum[info]
            for action, increment in increments.items():
                totals[action] += temporal_weight * increment

        self.iteration = t

    def run(self, iterations: int) -> None:
        if iterations < 0:
            raise ValueError("iterations must be non-negative")
        for _ in range(iterations):
            self.step()

    def stats(self) -> ThreeRoundFullTreeStats:
        return ThreeRoundFullTreeStats(
            iterations=self.iteration,
            terminal_evaluations=self.terminal_evaluations,
            infosets=len(self.regrets),
        )
