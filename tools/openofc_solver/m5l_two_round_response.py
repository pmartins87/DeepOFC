from __future__ import annotations

"""Fixed-opponent outcome-sampled response learner for M5L Q2.

This is the two-round analogue of the Q0/Q1 learned response.  It exists only to
measure underestimation against the independently implemented exact two-round
best response.  Nothing in this module is certification eligible by itself.
"""

from dataclasses import dataclass
import random
from typing import Mapping, Sequence

from deepofc.actions import NormalPlacementAction
from deepofc.hu_two_round import HUTwoRoundSubgame, StrategyProfile, TwoRoundInfoSet
from deepofc.hu_two_round_br import (
    TwoRoundBestResponse,
    profile_with_pure_response,
)

AUTHORITY = "M5L_TWO_ROUND_LEARNED_RESPONSE_CALIBRATION_ONLY"


def _normalize(values: Mapping[NormalPlacementAction, float]) -> dict[NormalPlacementAction, float]:
    if not values:
        raise ValueError("M5L two-round response requires legal actions")
    checked = {action: float(value) for action, value in values.items()}
    if any(value < 0.0 for value in checked.values()):
        raise ValueError("M5L two-round response received negative probability")
    total = sum(checked.values())
    if total <= 0.0:
        probability = 1.0 / len(checked)
        return {action: probability for action in checked}
    return {action: value / total for action, value in checked.items()}


def _sample_action(
    distribution: Mapping[NormalPlacementAction, float],
    rng: random.Random,
) -> tuple[NormalPlacementAction, float]:
    normalized = _normalize(distribution)
    target = rng.random()
    cumulative = 0.0
    last: NormalPlacementAction | None = None
    for action in sorted(normalized, key=lambda candidate: candidate.key()):
        last = action
        cumulative += normalized[action]
        if target < cumulative:
            return action, normalized[action]
    if last is None:
        raise AssertionError("M5L two-round response sampled empty distribution")
    return last, normalized[last]


@dataclass
class ResponseNode:
    actions: tuple[NormalPlacementAction, ...]
    regrets: list[float]
    cumulative_policy: list[float]
    visits: int = 0

    @classmethod
    def create(cls, actions: Sequence[NormalPlacementAction]) -> "ResponseNode":
        frozen = tuple(actions)
        if not frozen:
            raise ValueError("M5L response node requires actions")
        return cls(frozen, [0.0] * len(frozen), [0.0] * len(frozen))

    def current_policy(self) -> dict[NormalPlacementAction, float]:
        positive = [max(0.0, float(value)) for value in self.regrets]
        total = sum(positive)
        if total <= 0.0:
            return {action: 1.0 / len(self.actions) for action in self.actions}
        return {
            action: positive[index] / total
            for index, action in enumerate(self.actions)
        }

    def average_policy(self) -> dict[NormalPlacementAction, float]:
        total = sum(self.cumulative_policy)
        if total <= 0.0:
            return self.current_policy()
        return {
            action: self.cumulative_policy[index] / total
            for index, action in enumerate(self.actions)
        }


@dataclass(frozen=True)
class _OwnDecision:
    info: TwoRoundInfoSet
    action: NormalPlacementAction
    strategy: Mapping[NormalPlacementAction, float]
    current_probability: float
    my_reach_before: float
    sample_reach_before: float


@dataclass(frozen=True)
class TwoRoundResponseTrainingReport:
    persistent_player: int
    iterations: int
    infosets: int
    total_visits: int
    terminal_evaluations: int
    seed: int
    authority: str = AUTHORITY


@dataclass(frozen=True)
class TwoRoundPureResponseReport:
    persistent_player: int
    learned_infosets: int
    fallback_infosets: int
    total_response_infosets: int
    approximate_response_value: float
    exact_replay_terminals: int | None = None
    authority: str = AUTHORITY


class TwoRoundOutcomeSampledResponseLearner:
    """Learn one unilateral response against a frozen two-round opponent profile."""

    def __init__(
        self,
        game: HUTwoRoundSubgame,
        opponent_profile: StrategyProfile,
        *,
        deviator_player: int,
        epsilon: float = 0.6,
        seed: int = 1,
    ) -> None:
        if deviator_player not in (0, 1):
            raise ValueError("M5L two-round deviator must be P0 or P1")
        if not 0.0 < float(epsilon) <= 1.0:
            raise ValueError("M5L two-round epsilon must be in (0,1]")
        self.game = game
        self.opponent_profile = opponent_profile
        self.deviator_player = int(deviator_player)
        self.epsilon = float(epsilon)
        self.seed = int(seed)
        self.rng = random.Random(self.seed)
        self.nodes: dict[TwoRoundInfoSet, ResponseNode] = {}
        self.iterations = 0
        self.terminal_evaluations = 0

    def _node(self, info: TwoRoundInfoSet) -> ResponseNode:
        actions = tuple(self.game.actions(info))
        node = self.nodes.get(info)
        if node is None:
            node = ResponseNode.create(actions)
            self.nodes[info] = node
        elif node.actions != actions:
            raise AssertionError("M5L two-round infoset legal actions changed")
        return node

    def _response_target(self, info: TwoRoundInfoSet) -> dict[NormalPlacementAction, float]:
        return self._node(info).current_policy()

    def _sampling_distribution(
        self,
        target: Mapping[NormalPlacementAction, float],
    ) -> dict[NormalPlacementAction, float]:
        uniform = 1.0 / len(target)
        return {
            action: (1.0 - self.epsilon) * probability + self.epsilon * uniform
            for action, probability in target.items()
        }

    def _choose(
        self,
        info: TwoRoundInfoSet,
        *,
        q: float,
        my_reach: float,
        sample_reach_nochance: float,
        pi_minus_i: float,
        own_decisions: list[_OwnDecision],
    ) -> tuple[NormalPlacementAction, float, float, float, float]:
        if info.player == self.deviator_player:
            target = self._response_target(info)
            sampling = self._sampling_distribution(target)
            action, sampled_probability = _sample_action(sampling, self.rng)
            own_decisions.append(
                _OwnDecision(
                    info=info,
                    action=action,
                    strategy=target,
                    current_probability=float(target[action]),
                    my_reach_before=my_reach,
                    sample_reach_before=sample_reach_nochance,
                )
            )
            return (
                action,
                q * sampled_probability,
                my_reach * float(target[action]),
                sample_reach_nochance * sampled_probability,
                pi_minus_i,
            )

        target = self.game._distribution(self.opponent_profile, info)
        action, sampled_probability = _sample_action(target, self.rng)
        return (
            action,
            q * sampled_probability,
            my_reach,
            sample_reach_nochance * sampled_probability,
            pi_minus_i * float(target[action]),
        )

    def step(self) -> None:
        outcome = self.game.outcomes[self.rng.randrange(len(self.game.outcomes))]
        cp = float(self.game.chance_probability)
        q = cp
        pi_minus_i = cp
        my_reach = 1.0
        sample_reach_nochance = 1.0
        own_decisions: list[_OwnDecision] = []

        first = outcome.first_player
        second = outcome.second_player
        first_r3_info = self.game.round3_first_info(outcome)
        first_r3, q, my_reach, sample_reach_nochance, pi_minus_i = self._choose(
            first_r3_info,
            q=q,
            my_reach=my_reach,
            sample_reach_nochance=sample_reach_nochance,
            pi_minus_i=pi_minus_i,
            own_decisions=own_decisions,
        )

        second_r3_info = self.game.round3_second_info(outcome, first_r3)
        second_r3, q, my_reach, sample_reach_nochance, pi_minus_i = self._choose(
            second_r3_info,
            q=q,
            my_reach=my_reach,
            sample_reach_nochance=sample_reach_nochance,
            pi_minus_i=pi_minus_i,
            own_decisions=own_decisions,
        )

        _board0, _board1, action0_r3, action1_r3 = self.game._boards_after_round3(
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
        first_r4, q, my_reach, sample_reach_nochance, pi_minus_i = self._choose(
            first_r4_info,
            q=q,
            my_reach=my_reach,
            sample_reach_nochance=sample_reach_nochance,
            pi_minus_i=pi_minus_i,
            own_decisions=own_decisions,
        )

        second_r4_info = self.game.round4_info(
            outcome,
            player=second,
            own_round3_action=second_own_r3,
            opponent_round3_action=second_opp_r3,
            current_first_action=first_r4,
        )
        second_r4, q, my_reach, sample_reach_nochance, pi_minus_i = self._choose(
            second_r4_info,
            q=q,
            my_reach=my_reach,
            sample_reach_nochance=sample_reach_nochance,
            pi_minus_i=pi_minus_i,
            own_decisions=own_decisions,
        )

        u0 = float(
            self.game.terminal_u0(
                outcome, first_r3, second_r3, first_r4, second_r4
            )
        )
        utility = u0 if self.deviator_player == 0 else -u0
        self.terminal_evaluations += 1
        if q <= 0.0:
            raise AssertionError("M5L two-round sampled terminal has non-positive reach")

        future_own_probability = 1.0
        for decision in reversed(own_decisions):
            node = self.nodes[decision.info]
            weight = utility * pi_minus_i * future_own_probability / q
            for index, action in enumerate(node.actions):
                probability = float(decision.strategy[action])
                increment = weight * ((1.0 - probability) if action == decision.action else -probability)
                node.regrets[index] = max(0.0, node.regrets[index] + increment)
            future_own_probability *= decision.current_probability
            node.visits += 1

        # Mirror Q0's reach-corrected average-policy accumulator on every sampled
        # responding infoset.  Chance is excluded because the chance support is
        # already sampled uniformly and its common factor cancels in normalization.
        for decision in own_decisions:
            if decision.sample_reach_before <= 0.0:
                raise AssertionError("M5L two-round sample reach became non-positive")
            node = self.nodes[decision.info]
            scale = decision.my_reach_before / decision.sample_reach_before
            for index, action in enumerate(node.actions):
                node.cumulative_policy[index] += scale * float(decision.strategy[action])

        self.iterations += 1

    def run_to(self, target_iterations: int) -> TwoRoundResponseTrainingReport:
        if target_iterations < self.iterations:
            raise ValueError("M5L two-round learner cannot run backwards")
        while self.iterations < target_iterations:
            self.step()
        return TwoRoundResponseTrainingReport(
            persistent_player=self.deviator_player,
            iterations=self.iterations,
            infosets=len(self.nodes),
            total_visits=sum(node.visits for node in self.nodes.values()),
            terminal_evaluations=self.terminal_evaluations,
            seed=self.seed,
        )

    def pure_response(
        self,
        exact_reference: TwoRoundBestResponse,
    ) -> tuple[TwoRoundBestResponse, int, int]:
        if exact_reference.player != self.deviator_player:
            raise ValueError("M5L two-round exact reference player mismatch")
        choices: dict[TwoRoundInfoSet, NormalPlacementAction] = {}
        learned = 0
        fallback = 0
        for info in exact_reference.choices:
            actions = tuple(self.game.actions(info))
            node = self.nodes.get(info)
            if node is None:
                distribution = self.game._distribution(self.opponent_profile, info)
                best_probability = max(float(distribution[action]) for action in actions)
                eligible = [
                    action for action in actions
                    if abs(float(distribution[action]) - best_probability) <= 1e-15
                ]
                chosen = min(eligible, key=lambda action: action.key())
                fallback += 1
            else:
                average = node.average_policy()
                best_probability = max(float(average[action]) for action in actions)
                eligible = [
                    action for action in actions
                    if abs(float(average[action]) - best_probability) <= 1e-15
                ]
                chosen = min(eligible, key=lambda action: action.key())
                learned += 1
            choices[info] = chosen
        return (
            TwoRoundBestResponse(
                player=self.deviator_player,
                value=0.0,
                choices=choices,
            ),
            learned,
            fallback,
        )

    def exact_value_of_pure_response(
        self,
        response: TwoRoundBestResponse,
    ) -> float:
        full_profile = profile_with_pure_response(
            self.game,
            self.opponent_profile,
            response,
        )
        u0 = float(self.game.expected_u0(full_profile))
        return u0 if self.deviator_player == 0 else -u0
