from __future__ import annotations

from .actions import NormalPlacementAction
from .hu_two_round import HUTwoRoundSubgame, TwoRoundInfoSet
from .hu_two_round_mccfr import TwoRoundExternalSamplingMCCFR


class TwoRoundExternalSamplingReachAverage(TwoRoundExternalSamplingMCCFR):
    """External-sampling trainer with exact standard CFR averaging.

    The first implementation flushed every round-4 child whenever its round-3
    predecessor changed. That was mathematically exact but computationally
    hostile to sampling. This version keeps the same estimator while recording
    only behavioral-strategy change events. At export time it integrates the
    piecewise-constant product

        pi_i^t(I) * sigma_i^t(I, a)

    by merging the predecessor and local event timelines.

    For round 3, own reach is one. For round 4, perfect recall makes own reach
    exactly the probability of the remembered round-3 action at the unique
    predecessor infoset.
    """

    def __init__(self, game: HUTwoRoundSubgame, *, seed: int = 1) -> None:
        super().__init__(game, seed=seed)
        self.round4_parent: dict[
            TwoRoundInfoSet, tuple[TwoRoundInfoSet, NormalPlacementAction]
        ] = {}
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
            self.round4_parent[info] = (parent, candidates[0])

        # Implicit initial event at iteration 1 is uniform for every infoset.
        # Store only later changes: info -> [(first_iteration_used, distribution)].
        self.strategy_events: dict[
            TwoRoundInfoSet,
            list[tuple[int, dict[NormalPlacementAction, float]]],
        ] = {}

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

    def _uniform_distribution(
        self, info: TwoRoundInfoSet
    ) -> dict[NormalPlacementAction, float]:
        actions = self.game.actions(info)
        probability = 1.0 / len(actions)
        return {action: probability for action in actions}

    @staticmethod
    def _different(
        left: dict[NormalPlacementAction, float],
        right: dict[NormalPlacementAction, float],
    ) -> bool:
        return any(left[action] != right[action] for action in left)

    def step(self) -> None:
        t = self.iteration + 1
        delta: dict[TwoRoundInfoSet, dict[NormalPlacementAction, float]] = {}
        self._sampled_traversal(0, delta)
        self._sampled_traversal(1, delta)

        # Iteration t used these pre-update strategies. Preserve the legacy
        # local-time average exactly as in the base class.
        before = {info: self._distribution(info) for info in delta}
        for info in delta:
            self._flush_local_strategy_used_through(info, t)

        for info, action_delta in delta.items():
            for action, increment in action_delta.items():
                self.regrets[info][action] += increment
            self.local_active_since[info] = t + 1

        # Any changed behavioral strategy becomes active only at t+1. No child
        # infosets are touched here; reach-weighted products are integrated later.
        for info in delta:
            after = self._distribution(info)
            if self._different(before[info], after):
                self.strategy_events.setdefault(info, []).append((t + 1, dict(after)))
        self.iteration = t

    def _events_through(
        self, info: TwoRoundInfoSet
    ) -> list[tuple[int, dict[NormalPlacementAction, float]]]:
        events = [(1, self._uniform_distribution(info))]
        if self.iteration <= 0:
            return events
        for start, distribution in self.strategy_events.get(info, ()):  # sparse
            if start <= self.iteration:
                events.append((start, distribution))
        return events

    @staticmethod
    def _distribution_at(
        events: list[tuple[int, dict[NormalPlacementAction, float]]],
        iteration: int,
    ) -> dict[NormalPlacementAction, float]:
        current = events[0][1]
        for start, distribution in events[1:]:
            if start > iteration:
                break
            current = distribution
        return current

    def _integrate_round3(
        self, info: TwoRoundInfoSet
    ) -> tuple[dict[NormalPlacementAction, float], float]:
        actions = self.game.actions(info)
        totals = {action: 0.0 for action in actions}
        if self.iteration <= 0:
            return totals, 0.0
        events = self._events_through(info)
        starts = [start for start, _ in events] + [self.iteration + 1]
        mass = 0.0
        for index in range(len(starts) - 1):
            start, end = starts[index], starts[index + 1]
            count = end - start
            distribution = events[index][1]
            mass += count
            for action, probability in distribution.items():
                totals[action] += count * probability
        return totals, mass

    def _integrate_round4(
        self, info: TwoRoundInfoSet
    ) -> tuple[dict[NormalPlacementAction, float], float]:
        actions = self.game.actions(info)
        totals = {action: 0.0 for action in actions}
        if self.iteration <= 0:
            return totals, 0.0

        parent, parent_action = self.round4_parent[info]
        local_events = self._events_through(info)
        parent_events = self._events_through(parent)
        breakpoints = {1, self.iteration + 1}
        breakpoints.update(start for start, _ in local_events)
        breakpoints.update(start for start, _ in parent_events)
        ordered = sorted(point for point in breakpoints if point <= self.iteration + 1)

        mass = 0.0
        for start, end in zip(ordered, ordered[1:]):
            count = end - start
            if count <= 0:
                continue
            local = self._distribution_at(local_events, start)
            parent_distribution = self._distribution_at(parent_events, start)
            reach = parent_distribution[parent_action]
            weighted_count = count * reach
            mass += weighted_count
            for action, probability in local.items():
                totals[action] += weighted_count * probability
        return totals, mass

    def cfr_average_profile(self):
        if self.iteration == 0:
            return self.game.uniform_profile()

        profile = {}
        for info, actions in self.game.info_actions.items():
            if info.round_index == 3:
                totals, mass = self._integrate_round3(info)
            else:
                totals, mass = self._integrate_round4(info)

            if mass <= 0.0:
                probability = 1.0 / len(actions)
                profile[info] = {action: probability for action in actions}
            else:
                profile[info] = {
                    action: totals[action] / mass for action in actions
                }
        return profile
