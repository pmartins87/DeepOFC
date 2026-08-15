from __future__ import annotations

from collections import defaultdict

from .actions import NormalPlacementAction
from .hu_two_round import HUTwoRoundSubgame, TwoRoundInfoSet
from .hu_two_round_mccfr import TwoRoundExternalSamplingMCCFR


class TwoRoundExternalSamplingReachAverage(TwoRoundExternalSamplingMCCFR):
    """External-sampling trainer with exact standard CFR average integration.

    For a round-3 infoset, the player's own reach before acting is 1.
    For a round-4 infoset, perfect recall makes the own reach exactly the
    probability of the player's remembered round-3 action at its unique
    predecessor infoset.

    The standard average numerator is therefore integrated as

        sum_t pi_i^t(I) * sigma_i^t(I, a)

    and its denominator as sum_t pi_i^t(I).

    Both the predecessor strategy and the local strategy are piecewise constant
    between regret updates. The lazy integrator flushes a round-4 infoset when
    either component changes. This is exact for this two-decision benchmark and
    avoids scanning all ~80k infosets every sampled iteration.
    """

    def __init__(self, game: HUTwoRoundSubgame, *, seed: int = 1) -> None:
        super().__init__(game, seed=seed)
        self.reach_average_sum = {
            info: {action: 0.0 for action in actions}
            for info, actions in game.info_actions.items()
        }
        self.reach_average_mass = {info: 0.0 for info in game.info_actions}
        self.reach_average_active_since = {info: 1 for info in game.info_actions}

        self.round4_parent: dict[
            TwoRoundInfoSet, tuple[TwoRoundInfoSet, NormalPlacementAction]
        ] = {}
        children: dict[TwoRoundInfoSet, list[TwoRoundInfoSet]] = defaultdict(list)
        for info in game.info_actions:
            if info.round_index != 4:
                continue
            parent = self._parent_info(info)
            remembered_key = info.own_round3_action
            assert remembered_key is not None
            candidates = [
                action
                for action in game.actions(parent)
                if action.key() == remembered_key
            ]
            if len(candidates) != 1:
                raise AssertionError(
                    "round-4 perfect recall did not map to one predecessor action"
                )
            relation = (parent, candidates[0])
            self.round4_parent[info] = relation
            children[parent].append(info)
        self.children_by_parent = {
            parent: tuple(values) for parent, values in children.items()
        }

    @staticmethod
    def _parent_info(info: TwoRoundInfoSet) -> TwoRoundInfoSet:
        if info.round_index != 4:
            raise ValueError("only round-4 infosets have a predecessor relation")
        if info.role == "first":
            return TwoRoundInfoSet(
                player=info.player,
                round_index=3,
                role="first",
                own_round3_hand=info.own_round3_hand,
            )
        assert info.opponent_round3_public is not None
        return TwoRoundInfoSet(
            player=info.player,
            round_index=3,
            role="second",
            own_round3_hand=info.own_round3_hand,
            observed_current_first_public=info.opponent_round3_public,
        )

    def own_reach(self, info: TwoRoundInfoSet) -> float:
        if info.round_index == 3:
            return 1.0
        parent, parent_action = self.round4_parent[info]
        return self._distribution(parent)[parent_action]

    def _flush_reach_average_through(
        self,
        info: TwoRoundInfoSet,
        iteration: int,
    ) -> None:
        count = iteration - self.reach_average_active_since[info] + 1
        if count <= 0:
            return
        reach = self.own_reach(info)
        strategy = self._distribution(info)
        weighted_count = count * reach
        if weighted_count != 0.0:
            totals = self.reach_average_sum[info]
            for action, probability in strategy.items():
                totals[action] += weighted_count * probability
            self.reach_average_mass[info] += weighted_count
        self.reach_average_active_since[info] = iteration + 1

    def step(self) -> None:
        t = self.iteration + 1
        delta: dict[TwoRoundInfoSet, dict[NormalPlacementAction, float]] = {}
        self._sampled_traversal(0, delta)
        self._sampled_traversal(1, delta)

        changed = set(delta)
        to_flush = set(changed)
        for info in changed:
            if info.round_index == 3:
                to_flush.update(self.children_by_parent.get(info, ()))

        # Every strategy/reach pair below was the one actually used in iteration
        # t. Flush it before any regret changes; all new behavior begins at t+1.
        for info in to_flush:
            self._flush_reach_average_through(info, t)

        # Preserve the legacy local-time-average diagnostic from the base class.
        for info in changed:
            self._flush_local_strategy_used_through(info, t)

        for info, action_delta in delta.items():
            for action, increment in action_delta.items():
                self.regrets[info][action] += increment
            self.local_active_since[info] = t + 1
        self.iteration = t

    def cfr_average_profile(self):
        if self.iteration == 0:
            return self.game.uniform_profile()

        profile = {}
        for info, actions in self.game.info_actions.items():
            totals = dict(self.reach_average_sum[info])
            mass = self.reach_average_mass[info]
            count = self.iteration - self.reach_average_active_since[info] + 1
            if count > 0:
                reach = self.own_reach(info)
                weighted_count = count * reach
                strategy = self._distribution(info)
                for action, probability in strategy.items():
                    totals[action] += weighted_count * probability
                mass += weighted_count

            if mass <= 0.0:
                # Standard CFR leaves an unreachable average infoset without
                # behavioral mass. Use uniform only as a deterministic fallback
                # representation; it contributes no reach to the accumulated
                # average value that created the zero denominator.
                probability = 1.0 / len(actions)
                profile[info] = {action: probability for action in actions}
            else:
                profile[info] = {
                    action: totals[action] / mass for action in actions
                }
        return profile
