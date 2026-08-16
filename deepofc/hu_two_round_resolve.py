from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping

from .actions import NormalPlacementAction
from .hu_two_round import (
    HUTwoRoundSubgame,
    StrategyProfile,
    TwoRoundChanceOutcome,
    TwoRoundInfoSet,
    action_public_key,
)


@dataclass(frozen=True, order=True)
class Round4PublicState:
    """Information that is public after both round-3 placements are confirmed.

    The key intentionally contains neither player's discard, neither original
    private three-card hand, and neither future/private round-4 hand.
    """

    first_player: int
    first_round3_public: tuple[tuple[str, str], ...]
    second_round3_public: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class Round4HiddenHistory:
    outcome: TwoRoundChanceOutcome
    first_round3_action: NormalPlacementAction
    second_round3_action: NormalPlacementAction
    posterior_probability: float


class Round4PublicSubgame:
    """Exact one-street continuation game conditioned on one public state."""

    def __init__(
        self,
        parent: HUTwoRoundSubgame,
        public_state: Round4PublicState,
        histories: tuple[Round4HiddenHistory, ...],
        *,
        public_reach_probability: float,
    ) -> None:
        if not histories:
            raise ValueError("public subgame requires at least one hidden history")
        if public_reach_probability <= 0.0:
            raise ValueError("public reach probability must be positive")
        total = sum(h.posterior_probability for h in histories)
        if abs(total - 1.0) > 1e-12:
            raise ValueError(f"posterior probabilities must sum to one, got {total}")
        self.parent = parent
        self.public_state = public_state
        self.histories = histories
        self.public_reach_probability = float(public_reach_probability)
        self.info_actions = self._build_info_actions()

    def _split_round3(self, history: Round4HiddenHistory):
        outcome = history.outcome
        _, _, action0_r3, action1_r3 = self.parent._boards_after_round3(
            outcome,
            history.first_round3_action,
            history.second_round3_action,
        )
        first = outcome.first_player
        second = outcome.second_player
        first_own = action0_r3 if first == 0 else action1_r3
        first_opp = action1_r3 if first == 0 else action0_r3
        second_own = action0_r3 if second == 0 else action1_r3
        second_opp = action1_r3 if second == 0 else action0_r3
        return first_own, first_opp, second_own, second_opp

    def first_info(self, history: Round4HiddenHistory) -> TwoRoundInfoSet:
        outcome = history.outcome
        first_own, first_opp, _, _ = self._split_round3(history)
        return self.parent.round4_info(
            outcome,
            player=outcome.first_player,
            own_round3_action=first_own,
            opponent_round3_action=first_opp,
            current_first_action=None,
        )

    def second_info(
        self,
        history: Round4HiddenHistory,
        first_round4_action: NormalPlacementAction,
    ) -> TwoRoundInfoSet:
        outcome = history.outcome
        _, _, second_own, second_opp = self._split_round3(history)
        return self.parent.round4_info(
            outcome,
            player=outcome.second_player,
            own_round3_action=second_own,
            opponent_round3_action=second_opp,
            current_first_action=first_round4_action,
        )

    def _build_info_actions(self):
        out: dict[TwoRoundInfoSet, tuple[NormalPlacementAction, ...]] = {}
        for history in self.histories:
            first_info = self.first_info(history)
            out[first_info] = self.parent.actions(first_info)
            for first_action in out[first_info]:
                second_info = self.second_info(history, first_action)
                out[second_info] = self.parent.actions(second_info)
        return out

    def actions(self, info: TwoRoundInfoSet):
        return self.info_actions[info]

    def distribution(self, profile: StrategyProfile, info: TwoRoundInfoSet):
        legal = self.actions(info)
        supplied = profile.get(info)
        if supplied is None:
            p = 1.0 / len(legal)
            return {action: p for action in legal}
        illegal = set(supplied) - set(legal)
        if illegal:
            raise ValueError("strategy contains illegal continuation actions")
        weights = {action: float(supplied.get(action, 0.0)) for action in legal}
        if any(value < 0.0 for value in weights.values()):
            raise ValueError("strategy probabilities cannot be negative")
        total = sum(weights.values())
        if total <= 0.0:
            raise ValueError("strategy probabilities need positive mass")
        return {action: value / total for action, value in weights.items()}

    def uniform_profile(self):
        return {
            info: {action: 1.0 / len(actions) for action in actions}
            for info, actions in self.info_actions.items()
        }

    def terminal_u0(
        self,
        history: Round4HiddenHistory,
        first_round4_action: NormalPlacementAction,
        second_round4_action: NormalPlacementAction,
    ) -> int:
        return self.parent.terminal_u0(
            history.outcome,
            history.first_round3_action,
            history.second_round3_action,
            first_round4_action,
            second_round4_action,
        )

    def expected_u0(self, profile: StrategyProfile) -> float:
        total = 0.0
        for history in self.histories:
            q = history.posterior_probability
            first_info = self.first_info(history)
            first_dist = self.distribution(profile, first_info)
            for first_action, p_first in first_dist.items():
                second_info = self.second_info(history, first_action)
                second_dist = self.distribution(profile, second_info)
                for second_action, p_second in second_dist.items():
                    total += q * p_first * p_second * self.terminal_u0(
                        history, first_action, second_action
                    )
        return total

    def best_response_value(self, profile: StrategyProfile, player: int) -> float:
        if player not in (0, 1):
            raise ValueError("player must be 0 or 1")
        action_values: dict[TwoRoundInfoSet, dict[NormalPlacementAction, float]] = {}

        if self.public_state.first_player == player:
            for history in self.histories:
                q = history.posterior_probability
                info = self.first_info(history)
                bucket = action_values.setdefault(
                    info, {action: 0.0 for action in self.actions(info)}
                )
                for first_action in self.actions(info):
                    second_info = self.second_info(history, first_action)
                    opp_dist = self.distribution(profile, second_info)
                    continuation = 0.0
                    for second_action, probability in opp_dist.items():
                        u0 = self.terminal_u0(history, first_action, second_action)
                        own = float(u0 if player == 0 else -u0)
                        continuation += probability * own
                    bucket[first_action] += q * continuation
        else:
            for history in self.histories:
                q = history.posterior_probability
                first_info = self.first_info(history)
                opp_dist = self.distribution(profile, first_info)
                for first_action, p_first in opp_dist.items():
                    info = self.second_info(history, first_action)
                    bucket = action_values.setdefault(
                        info, {action: 0.0 for action in self.actions(info)}
                    )
                    for second_action in self.actions(info):
                        u0 = self.terminal_u0(history, first_action, second_action)
                        own = float(u0 if player == 0 else -u0)
                        bucket[second_action] += q * p_first * own

        return sum(max(values.values()) for values in action_values.values())

    def nash_conv(self, profile: StrategyProfile) -> float:
        return self.best_response_value(profile, 0) + self.best_response_value(profile, 1)

    def exploitability(self, profile: StrategyProfile) -> float:
        return 0.5 * self.nash_conv(profile)


class Round4PublicDCFR:
    """Deterministic full-tree DCFR for one conditioned public continuation."""

    def __init__(
        self,
        game: Round4PublicSubgame,
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
        self.regrets = {
            info: {action: 0.0 for action in actions}
            for info, actions in game.info_actions.items()
        }
        self.strategy_sum = {
            info: {action: 0.0 for action in actions}
            for info, actions in game.info_actions.items()
        }

    def distribution(self, info: TwoRoundInfoSet):
        positive = {
            action: max(0.0, regret)
            for action, regret in self.regrets[info].items()
        }
        total = sum(positive.values())
        if total <= 0.0:
            p = 1.0 / len(positive)
            return {action: p for action in positive}
        return {action: value / total for action, value in positive.items()}

    def current_profile(self):
        return {info: self.distribution(info) for info in self.game.info_actions}

    def average_profile(self):
        profile = {}
        for info, totals in self.strategy_sum.items():
            mass = sum(totals.values())
            if mass <= 0.0:
                p = 1.0 / len(totals)
                profile[info] = {action: p for action in totals}
            else:
                profile[info] = {action: value / mass for action, value in totals.items()}
        return profile

    @staticmethod
    def _own_regret(actor: int, action_u0: float, node_u0: float) -> float:
        return action_u0 - node_u0 if actor == 0 else node_u0 - action_u0

    def step(self) -> None:
        t = self.iteration + 1
        current = self.current_profile()
        regret_delta = {
            info: {action: 0.0 for action in actions}
            for info, actions in self.game.info_actions.items()
        }

        # Both players have only one decision in this conditioned continuation,
        # so their own sequence reach before that decision is one. Integrate the
        # local behavioral strategy once per iteration, independent of chance.
        avg_weight = float(t) ** self.gamma
        for info, distribution in current.items():
            for action, probability in distribution.items():
                self.strategy_sum[info][action] += avg_weight * probability

        for history in self.game.histories:
            q = history.posterior_probability
            first = history.outcome.first_player
            second = history.outcome.second_player
            first_info = self.game.first_info(history)
            first_dist = current[first_info]
            first_values: dict[NormalPlacementAction, float] = {}

            for first_action, p_first in first_dist.items():
                second_info = self.game.second_info(history, first_action)
                second_dist = current[second_info]
                second_values = {
                    second_action: float(
                        self.game.terminal_u0(history, first_action, second_action)
                    )
                    for second_action in second_dist
                }
                second_node = sum(
                    second_dist[action] * value
                    for action, value in second_values.items()
                )
                for action, value in second_values.items():
                    regret_delta[second_info][action] += (
                        q * p_first * self._own_regret(second, value, second_node)
                    )
                first_values[first_action] = second_node

            first_node = sum(
                first_dist[action] * value for action, value in first_values.items()
            )
            for action, value in first_values.items():
                regret_delta[first_info][action] += (
                    q * self._own_regret(first, value, first_node)
                )

        pos_power = float(t) ** self.alpha
        neg_power = float(t) ** self.beta
        pos_factor = pos_power / (pos_power + 1.0)
        neg_factor = neg_power / (neg_power + 1.0)
        for values in self.regrets.values():
            for action, old in tuple(values.items()):
                values[action] = old * (pos_factor if old >= 0.0 else neg_factor)

        for info, delta in regret_delta.items():
            for action, increment in delta.items():
                updated = self.regrets[info][action] + increment
                if not isfinite(updated):
                    raise FloatingPointError("non-finite public-state regret")
                self.regrets[info][action] = updated
        self.iteration = t

    def run(self, iterations: int) -> None:
        if iterations < 0:
            raise ValueError("iterations must be non-negative")
        for _ in range(iterations):
            self.step()


def build_round4_public_subgames(
    game: HUTwoRoundSubgame,
    blueprint: StrategyProfile,
) -> dict[Round4PublicState, Round4PublicSubgame]:
    """Condition the exact round-4 continuation on public round-3 history.

    Posterior mass uses only chance and the blueprint's round-3 behavioral
    probabilities. No round-4 private information is inserted into the public
    key; it remains inside `Round4HiddenHistory` and the players' infosets.
    """

    raw: dict[Round4PublicState, list[tuple[TwoRoundChanceOutcome, NormalPlacementAction, NormalPlacementAction, float]]] = {}
    total_public_mass = 0.0
    cp = game.chance_probability

    for outcome in game.outcomes:
        first_info = game.round3_first_info(outcome)
        first_dist = game._distribution(blueprint, first_info)
        for first_r3, p_first in first_dist.items():
            second_info = game.round3_second_info(outcome, first_r3)
            second_dist = game._distribution(blueprint, second_info)
            for second_r3, p_second in second_dist.items():
                reach = cp * p_first * p_second
                if reach <= 0.0:
                    continue
                state = Round4PublicState(
                    first_player=outcome.first_player,
                    first_round3_public=action_public_key(first_r3),
                    second_round3_public=action_public_key(second_r3),
                )
                raw.setdefault(state, []).append((outcome, first_r3, second_r3, reach))
                total_public_mass += reach

    if abs(total_public_mass - 1.0) > 1e-10:
        raise AssertionError(f"public-state reach mass must sum to one, got {total_public_mass}")

    result = {}
    for state, items in raw.items():
        mass = sum(item[3] for item in items)
        histories = tuple(
            Round4HiddenHistory(
                outcome=outcome,
                first_round3_action=first_r3,
                second_round3_action=second_r3,
                posterior_probability=reach / mass,
            )
            for outcome, first_r3, second_r3, reach in items
        )
        result[state] = Round4PublicSubgame(
            game,
            state,
            histories,
            public_reach_probability=mass,
        )
    return result
