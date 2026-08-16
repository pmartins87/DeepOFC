from __future__ import annotations

import random
from dataclasses import dataclass

from .actions import NormalPlacementAction
from .hu_three_round_sequential import (
    HUThreeRoundSequentialSubgame,
    StrategyProfile,
)
from .sequential import HUPlayerObservation, HUSequentialNormalState


@dataclass(frozen=True)
class ThreeRoundTrainingStats:
    iterations: int
    terminal_evaluations: int
    regret_infosets: int


class HUThreeRoundExternalSamplingMCCFR:
    """Recursive external-sampling MCCFR on the canonical sequential engine.

    Chance and opponent actions are sampled. At the traverser's information
    sets every legal action is expanded. Both player traversals in one global
    iteration read the same pre-update regret tables; deltas are committed only
    after both traversals, matching the simultaneous-update convention used by
    the already certified two-round solver.
    """

    def __init__(
        self,
        game: HUThreeRoundSequentialSubgame,
        *,
        seed: int = 1,
    ) -> None:
        self.game = game
        self.rng = random.Random(seed)
        self.seed = int(seed)
        self.iteration = 0
        self.terminal_evaluations = 0
        self.regrets: dict[
            HUPlayerObservation, dict[NormalPlacementAction, float]
        ] = {}

    def _ensure_info(
        self, info: HUPlayerObservation
    ) -> dict[NormalPlacementAction, float]:
        values = self.regrets.get(info)
        if values is None:
            values = {action: 0.0 for action in self.game.actions(info)}
            self.regrets[info] = values
        return values

    def _distribution(
        self, info: HUPlayerObservation
    ) -> dict[NormalPlacementAction, float]:
        regrets = self._ensure_info(info)
        positive = {action: max(0.0, value) for action, value in regrets.items()}
        total = sum(positive.values())
        if total <= 0.0:
            p = 1.0 / len(positive)
            return {action: p for action in positive}
        return {action: value / total for action, value in positive.items()}

    def current_profile(self) -> dict[
        HUPlayerObservation, dict[NormalPlacementAction, float]
    ]:
        # Sparse by design. Missing infosets retain uniform behavior through the
        # game's `distribution()` fallback when exact evaluation/BR traverses
        # branches never sampled during training.
        return {info: self._distribution(info) for info in tuple(self.regrets)}

    def _sample_action(
        self,
        distribution: dict[NormalPlacementAction, float],
    ) -> NormalPlacementAction:
        draw = self.rng.random()
        cumulative = 0.0
        last = None
        for action, probability in distribution.items():
            last = action
            cumulative += probability
            if draw <= cumulative:
                return action
        assert last is not None
        return last

    def _traverse(
        self,
        state: HUSequentialNormalState,
        traverser: int,
        delta: dict[HUPlayerObservation, dict[NormalPlacementAction, float]],
    ) -> float:
        if state.terminal:
            self.terminal_evaluations += 1
            u0 = float(self.game.terminal_u0(state))
            return u0 if traverser == 0 else -u0

        info = self.game.info(state)
        actor = state.acting_chair
        strategy = self._distribution(info)

        if actor != traverser:
            action = self._sample_action(strategy)
            return self._traverse(state.apply(action), traverser, delta)

        action_values: dict[NormalPlacementAction, float] = {}
        node_value = 0.0
        for action, probability in strategy.items():
            value = self._traverse(state.apply(action), traverser, delta)
            action_values[action] = value
            node_value += probability * value

        bucket = delta.setdefault(
            info,
            {action: 0.0 for action in self.game.actions(info)},
        )
        for action, value in action_values.items():
            bucket[action] += value - node_value
        return node_value

    def step(self) -> None:
        delta: dict[HUPlayerObservation, dict[NormalPlacementAction, float]] = {}
        for traverser in (0, 1):
            outcome = self.game.outcomes[self.rng.randrange(len(self.game.outcomes))]
            self._traverse(self.game.initial_state(outcome), traverser, delta)

        for info, increments in delta.items():
            regrets = self._ensure_info(info)
            for action, increment in increments.items():
                regrets[action] += increment
        self.iteration += 1

    def run(self, iterations: int) -> None:
        if iterations < 0:
            raise ValueError("iterations must be non-negative")
        for _ in range(iterations):
            self.step()

    def stats(self) -> ThreeRoundTrainingStats:
        return ThreeRoundTrainingStats(
            iterations=self.iteration,
            terminal_evaluations=self.terminal_evaluations,
            regret_infosets=len(self.regrets),
        )
