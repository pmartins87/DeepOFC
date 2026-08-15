from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Mapping

from .actions import NormalPlacementAction
from .hu_two_round import HUTwoRoundSubgame, TwoRoundChanceOutcome, TwoRoundInfoSet
from .hu_two_round_br import exact_nash_conv


@dataclass(frozen=True)
class TwoRoundMCCFRSnapshot:
    iteration: int
    profile_kind: str
    expected_u0: float
    br0: float
    br1: float
    nash_conv: float
    exploitability: float


class TwoRoundExternalSamplingMCCFR:
    """External-sampling MCCFR training kernel for the two-round HU benchmark.

    Chance and all non-traverser decisions are sampled according to their
    current distributions. Every traverser action is enumerated. A global
    iteration performs one traversal for P0 and one for P1 against the same
    pre-update regret tables; deltas are applied only after both traversals.

    The class exposes two evaluated policies:

    * `current_profile()` -- current regret-matching behavior;
    * `behavioral_time_average_profile()` -- exact unweighted time average of
      each local behavioral strategy.

    The latter is intentionally NOT called a CFR average. With repeated own
    decisions, standard CFR averaging requires own-reach weighting. Keeping the
    local time average separately lets us test it empirically without silently
    claiming a convergence theorem it does not have. A later R6 candidate may
    add a separately validated reach-weighted sampling estimator.
    """

    def __init__(self, game: HUTwoRoundSubgame, *, seed: int = 1) -> None:
        self.game = game
        self.rng = random.Random(seed)
        self.iteration = 0
        self.regrets = {
            info: {action: 0.0 for action in actions}
            for info, actions in game.info_actions.items()
        }
        self.local_strategy_sum = {
            info: {action: 0.0 for action in actions}
            for info, actions in game.info_actions.items()
        }
        self.local_active_since = {info: 1 for info in game.info_actions}

    def _distribution(self, info: TwoRoundInfoSet) -> dict[NormalPlacementAction, float]:
        regrets = self.regrets[info]
        positive = {action: max(0.0, regret) for action, regret in regrets.items()}
        total = sum(positive.values())
        if total <= 0.0:
            probability = 1.0 / len(positive)
            return {action: probability for action in positive}
        return {action: value / total for action, value in positive.items()}

    def _sample_action(
        self,
        distribution: Mapping[NormalPlacementAction, float],
    ) -> NormalPlacementAction:
        threshold = self.rng.random()
        cumulative = 0.0
        last: NormalPlacementAction | None = None
        for action in sorted(distribution, key=lambda candidate: candidate.key()):
            last = action
            cumulative += distribution[action]
            if threshold <= cumulative:
                return action
        if last is None:
            raise RuntimeError("cannot sample an empty action distribution")
        return last

    @staticmethod
    def _own_utility(u0: float, traverser: int) -> float:
        return u0 if traverser == 0 else -u0

    def _accumulate_regret(
        self,
        delta: dict[TwoRoundInfoSet, dict[NormalPlacementAction, float]],
        info: TwoRoundInfoSet,
        action_values: dict[NormalPlacementAction, float],
        node_value: float,
    ) -> None:
        bucket = delta.setdefault(
            info,
            {action: 0.0 for action in self.game.actions(info)},
        )
        for action, value in action_values.items():
            bucket[action] += value - node_value

    def _stage_round4_second(
        self,
        outcome: TwoRoundChanceOutcome,
        first_r3: NormalPlacementAction,
        second_r3: NormalPlacementAction,
        first_r4: NormalPlacementAction,
        traverser: int,
        delta: dict[TwoRoundInfoSet, dict[NormalPlacementAction, float]],
    ) -> float:
        first = outcome.first_player
        second = outcome.second_player
        _, _, action0_r3, action1_r3 = self.game._boards_after_round3(
            outcome, first_r3, second_r3
        )
        second_own_r3 = action0_r3 if second == 0 else action1_r3
        second_opp_r3 = action1_r3 if second == 0 else action0_r3
        info = self.game.round4_info(
            outcome,
            player=second,
            own_round3_action=second_own_r3,
            opponent_round3_action=second_opp_r3,
            current_first_action=first_r4,
        )
        strategy = self._distribution(info)

        if second != traverser:
            sampled = self._sample_action(strategy)
            u0 = float(
                self.game.terminal_u0(
                    outcome, first_r3, second_r3, first_r4, sampled
                )
            )
            return self._own_utility(u0, traverser)

        values: dict[NormalPlacementAction, float] = {}
        node_value = 0.0
        for action, probability in strategy.items():
            u0 = float(
                self.game.terminal_u0(
                    outcome, first_r3, second_r3, first_r4, action
                )
            )
            value = self._own_utility(u0, traverser)
            values[action] = value
            node_value += probability * value
        self._accumulate_regret(delta, info, values, node_value)
        return node_value

    def _stage_round4_first(
        self,
        outcome: TwoRoundChanceOutcome,
        first_r3: NormalPlacementAction,
        second_r3: NormalPlacementAction,
        traverser: int,
        delta: dict[TwoRoundInfoSet, dict[NormalPlacementAction, float]],
    ) -> float:
        first = outcome.first_player
        _, _, action0_r3, action1_r3 = self.game._boards_after_round3(
            outcome, first_r3, second_r3
        )
        first_own_r3 = action0_r3 if first == 0 else action1_r3
        first_opp_r3 = action1_r3 if first == 0 else action0_r3
        info = self.game.round4_info(
            outcome,
            player=first,
            own_round3_action=first_own_r3,
            opponent_round3_action=first_opp_r3,
            current_first_action=None,
        )
        strategy = self._distribution(info)

        if first != traverser:
            sampled = self._sample_action(strategy)
            return self._stage_round4_second(
                outcome, first_r3, second_r3, sampled, traverser, delta
            )

        values: dict[NormalPlacementAction, float] = {}
        node_value = 0.0
        for action, probability in strategy.items():
            value = self._stage_round4_second(
                outcome, first_r3, second_r3, action, traverser, delta
            )
            values[action] = value
            node_value += probability * value
        self._accumulate_regret(delta, info, values, node_value)
        return node_value

    def _stage_round3_second(
        self,
        outcome: TwoRoundChanceOutcome,
        first_r3: NormalPlacementAction,
        traverser: int,
        delta: dict[TwoRoundInfoSet, dict[NormalPlacementAction, float]],
    ) -> float:
        second = outcome.second_player
        info = self.game.round3_second_info(outcome, first_r3)
        strategy = self._distribution(info)

        if second != traverser:
            sampled = self._sample_action(strategy)
            return self._stage_round4_first(
                outcome, first_r3, sampled, traverser, delta
            )

        values: dict[NormalPlacementAction, float] = {}
        node_value = 0.0
        for action, probability in strategy.items():
            value = self._stage_round4_first(
                outcome, first_r3, action, traverser, delta
            )
            values[action] = value
            node_value += probability * value
        self._accumulate_regret(delta, info, values, node_value)
        return node_value

    def _stage_round3_first(
        self,
        outcome: TwoRoundChanceOutcome,
        traverser: int,
        delta: dict[TwoRoundInfoSet, dict[NormalPlacementAction, float]],
    ) -> float:
        first = outcome.first_player
        info = self.game.round3_first_info(outcome)
        strategy = self._distribution(info)

        if first != traverser:
            sampled = self._sample_action(strategy)
            return self._stage_round3_second(outcome, sampled, traverser, delta)

        values: dict[NormalPlacementAction, float] = {}
        node_value = 0.0
        for action, probability in strategy.items():
            value = self._stage_round3_second(
                outcome, action, traverser, delta
            )
            values[action] = value
            node_value += probability * value
        self._accumulate_regret(delta, info, values, node_value)
        return node_value

    def _sampled_traversal(
        self,
        traverser: int,
        delta: dict[TwoRoundInfoSet, dict[NormalPlacementAction, float]],
    ) -> None:
        outcome = self.game.outcomes[self.rng.randrange(len(self.game.outcomes))]
        self._stage_round3_first(outcome, traverser, delta)

    def _flush_local_strategy_used_through(
        self,
        info: TwoRoundInfoSet,
        iteration: int,
    ) -> None:
        count = iteration - self.local_active_since[info] + 1
        if count <= 0:
            return
        strategy = self._distribution(info)
        totals = self.local_strategy_sum[info]
        for action, probability in strategy.items():
            totals[action] += count * probability

    def step(self) -> None:
        t = self.iteration + 1
        delta: dict[TwoRoundInfoSet, dict[NormalPlacementAction, float]] = {}
        self._sampled_traversal(0, delta)
        self._sampled_traversal(1, delta)

        for info, values in delta.items():
            # Iteration t used the pre-update local strategy. Credit that exact
            # interval before changing regrets; new behavior starts at t+1.
            self._flush_local_strategy_used_through(info, t)
            regrets = self.regrets[info]
            for action, increment in values.items():
                regrets[action] += increment
            self.local_active_since[info] = t + 1
        self.iteration = t

    def run(self, iterations: int) -> None:
        if iterations < 0:
            raise ValueError("iterations must be non-negative")
        for _ in range(iterations):
            self.step()

    def current_profile(self):
        return {info: self._distribution(info) for info in self.game.info_actions}

    def behavioral_time_average_profile(self):
        if self.iteration == 0:
            return self.game.uniform_profile()
        profile = {}
        for info, actions in self.game.info_actions.items():
            totals = dict(self.local_strategy_sum[info])
            count = self.iteration - self.local_active_since[info] + 1
            if count > 0:
                current = self._distribution(info)
                for action, probability in current.items():
                    totals[action] += count * probability
            mass = sum(totals.values())
            if mass <= 0.0:
                probability = 1.0 / len(actions)
                profile[info] = {action: probability for action in actions}
            else:
                profile[info] = {
                    action: totals[action] / mass for action in actions
                }
        return profile

    def snapshot(self, *, profile_kind: str = "current") -> TwoRoundMCCFRSnapshot:
        if profile_kind == "current":
            profile = self.current_profile()
        elif profile_kind == "behavioral_time_average":
            profile = self.behavioral_time_average_profile()
        else:
            raise ValueError(f"unsupported profile_kind: {profile_kind}")
        expected = self.game.expected_u0(profile)
        nash_conv, br0, br1 = exact_nash_conv(self.game, profile)
        return TwoRoundMCCFRSnapshot(
            iteration=self.iteration,
            profile_kind=profile_kind,
            expected_u0=expected,
            br0=br0.value,
            br1=br1.value,
            nash_conv=nash_conv,
            exploitability=0.5 * nash_conv,
        )
