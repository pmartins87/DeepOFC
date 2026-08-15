from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Mapping

from .actions import NormalPlacementAction
from .hu_two_round import HUTwoRoundSubgame, TwoRoundInfoSet
from .hu_two_round_br import exact_nash_conv


@dataclass(frozen=True)
class OutcomeMCCFRSnapshot:
    iteration: int
    expected_u0: float
    br0: float
    br1: float
    nash_conv: float
    exploitability: float
    training_terminal_evaluations: int


@dataclass(frozen=True)
class _OwnDecision:
    info: TwoRoundInfoSet
    action: NormalPlacementAction
    current_probability: float
    strategy: Mapping[NormalPlacementAction, float]


class TwoRoundOutcomeSamplingMCCFR:
    """Outcome-sampling MCCFR candidate for the two-round HU benchmark.

    Each traversal samples exactly one complete terminal history. Chance and the
    opponent are sampled from the current profile. The traverser's actions are
    sampled from an epsilon-greedy mixture of the current profile and uniform
    exploration, guaranteeing positive sampling probability for every legal
    action.

    Regret updates implement Lanctot et al. (NIPS 2009), Eq. 10. This class
    deliberately exposes only the current regret-matching profile until a
    reach-weighted average-strategy estimator is separately validated.
    """

    def __init__(
        self,
        game: HUTwoRoundSubgame,
        *,
        seed: int = 1,
        epsilon: float = 0.6,
    ) -> None:
        if not (0.0 < epsilon <= 1.0):
            raise ValueError("epsilon must be in (0, 1]")
        self.game = game
        self.rng = random.Random(seed)
        self.epsilon = float(epsilon)
        self.iteration = 0
        self.training_terminal_evaluations = 0
        self.regrets = {
            info: {action: 0.0 for action in actions}
            for info, actions in game.info_actions.items()
        }

    def _distribution(self, info: TwoRoundInfoSet) -> dict[NormalPlacementAction, float]:
        regrets = self.regrets[info]
        positive = {action: max(0.0, regret) for action, regret in regrets.items()}
        total = sum(positive.values())
        if total <= 0.0:
            probability = 1.0 / len(positive)
            return {action: probability for action in positive}
        return {action: value / total for action, value in positive.items()}

    def _sampling_distribution(
        self,
        info: TwoRoundInfoSet,
        traverser: int,
        current: Mapping[NormalPlacementAction, float],
    ) -> dict[NormalPlacementAction, float]:
        if info.player != traverser:
            return dict(current)
        uniform = 1.0 / len(current)
        keep = 1.0 - self.epsilon
        return {
            action: keep * probability + self.epsilon * uniform
            for action, probability in current.items()
        }

    def _sample_action(
        self,
        distribution: Mapping[NormalPlacementAction, float],
    ) -> tuple[NormalPlacementAction, float]:
        threshold = self.rng.random()
        cumulative = 0.0
        last: NormalPlacementAction | None = None
        for action in sorted(distribution, key=lambda candidate: candidate.key()):
            last = action
            cumulative += distribution[action]
            if threshold <= cumulative:
                return action, distribution[action]
        if last is None:
            raise RuntimeError("cannot sample empty distribution")
        return last, distribution[last]

    def _sample_terminal_and_delta(
        self,
        traverser: int,
    ) -> dict[TwoRoundInfoSet, dict[NormalPlacementAction, float]]:
        outcome = self.game.outcomes[self.rng.randrange(len(self.game.outcomes))]
        chance_probability = self.game.chance_probability
        q = chance_probability
        pi_minus_i = chance_probability
        own_decisions: list[_OwnDecision] = []

        first = outcome.first_player
        second = outcome.second_player

        first_r3_info = self.game.round3_first_info(outcome)
        first_r3_current = self._distribution(first_r3_info)
        first_r3_sampling = self._sampling_distribution(
            first_r3_info, traverser, first_r3_current
        )
        first_r3, first_r3_q = self._sample_action(first_r3_sampling)
        q *= first_r3_q
        if first == traverser:
            own_decisions.append(
                _OwnDecision(
                    info=first_r3_info,
                    action=first_r3,
                    current_probability=first_r3_current[first_r3],
                    strategy=first_r3_current,
                )
            )
        else:
            pi_minus_i *= first_r3_current[first_r3]

        second_r3_info = self.game.round3_second_info(outcome, first_r3)
        second_r3_current = self._distribution(second_r3_info)
        second_r3_sampling = self._sampling_distribution(
            second_r3_info, traverser, second_r3_current
        )
        second_r3, second_r3_q = self._sample_action(second_r3_sampling)
        q *= second_r3_q
        if second == traverser:
            own_decisions.append(
                _OwnDecision(
                    info=second_r3_info,
                    action=second_r3,
                    current_probability=second_r3_current[second_r3],
                    strategy=second_r3_current,
                )
            )
        else:
            pi_minus_i *= second_r3_current[second_r3]

        _, _, action0_r3, action1_r3 = self.game._boards_after_round3(
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
        first_r4_current = self._distribution(first_r4_info)
        first_r4_sampling = self._sampling_distribution(
            first_r4_info, traverser, first_r4_current
        )
        first_r4, first_r4_q = self._sample_action(first_r4_sampling)
        q *= first_r4_q
        if first == traverser:
            own_decisions.append(
                _OwnDecision(
                    info=first_r4_info,
                    action=first_r4,
                    current_probability=first_r4_current[first_r4],
                    strategy=first_r4_current,
                )
            )
        else:
            pi_minus_i *= first_r4_current[first_r4]

        second_r4_info = self.game.round4_info(
            outcome,
            player=second,
            own_round3_action=second_own_r3,
            opponent_round3_action=second_opp_r3,
            current_first_action=first_r4,
        )
        second_r4_current = self._distribution(second_r4_info)
        second_r4_sampling = self._sampling_distribution(
            second_r4_info, traverser, second_r4_current
        )
        second_r4, second_r4_q = self._sample_action(second_r4_sampling)
        q *= second_r4_q
        if second == traverser:
            own_decisions.append(
                _OwnDecision(
                    info=second_r4_info,
                    action=second_r4,
                    current_probability=second_r4_current[second_r4],
                    strategy=second_r4_current,
                )
            )
        else:
            pi_minus_i *= second_r4_current[second_r4]

        u0 = float(
            self.game.terminal_u0(
                outcome, first_r3, second_r3, first_r4, second_r4
            )
        )
        self.training_terminal_evaluations += 1
        utility = u0 if traverser == 0 else -u0
        if q <= 0.0:
            raise FloatingPointError("outcome sampling produced non-positive q(z)")

        delta: dict[TwoRoundInfoSet, dict[NormalPlacementAction, float]] = {}
        future_own_probability = 1.0
        for decision in reversed(own_decisions):
            weight = utility * pi_minus_i * future_own_probability / q
            bucket = delta.setdefault(
                decision.info,
                {action: 0.0 for action in self.game.actions(decision.info)},
            )
            for action, probability in decision.strategy.items():
                if action == decision.action:
                    bucket[action] += weight * (1.0 - probability)
                else:
                    bucket[action] -= weight * probability
            future_own_probability *= decision.current_probability
        return delta

    def step(self) -> None:
        combined: dict[TwoRoundInfoSet, dict[NormalPlacementAction, float]] = {}
        # Both traversals use exactly the same pre-update regret tables.
        for traverser in (0, 1):
            delta = self._sample_terminal_and_delta(traverser)
            for info, values in delta.items():
                bucket = combined.setdefault(
                    info,
                    {action: 0.0 for action in self.game.actions(info)},
                )
                for action, increment in values.items():
                    bucket[action] += increment

        for info, values in combined.items():
            regrets = self.regrets[info]
            for action, increment in values.items():
                regrets[action] += increment
        self.iteration += 1

    def run(self, iterations: int) -> None:
        if iterations < 0:
            raise ValueError("iterations must be non-negative")
        for _ in range(iterations):
            self.step()

    def current_profile(self):
        return {info: self._distribution(info) for info in self.game.info_actions}

    def snapshot(self) -> OutcomeMCCFRSnapshot:
        profile = self.current_profile()
        expected = self.game.expected_u0(profile)
        nash_conv, br0, br1 = exact_nash_conv(self.game, profile)
        return OutcomeMCCFRSnapshot(
            iteration=self.iteration,
            expected_u0=expected,
            br0=br0.value,
            br1=br1.value,
            nash_conv=nash_conv,
            exploitability=0.5 * nash_conv,
            training_terminal_evaluations=self.training_terminal_evaluations,
        )
