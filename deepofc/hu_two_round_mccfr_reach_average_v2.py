from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass

from .actions import NormalPlacementAction
from .hu_two_round import HUTwoRoundSubgame, TwoRoundInfoSet
from .hu_two_round_mccfr import TwoRoundExternalSamplingMCCFR


@dataclass(frozen=True)
class _ParentSegment:
    start: int
    end: int
    distribution: dict[NormalPlacementAction, float]
    cumulative_before: dict[NormalPlacementAction, float]


class TwoRoundExternalSamplingReachAverageV2(TwoRoundExternalSamplingMCCFR):
    """Exact standard CFR average with segment-based predecessor reach integration.

    R3 infosets have own reach 1, so their standard CFR average is simply the
    exact local time average already maintained by the base external-sampling
    solver.

    R4 own reach equals the probability of the remembered own R3 action at the
    unique perfect-recall predecessor. Instead of flushing every R4 child when
    a predecessor strategy changes, V2 records a closed time segment for the
    predecessor. Each R4 infoset integrates predecessor reach only when its own
    local strategy changes (or when the final average is queried).

    This removes the O(all descendants) work from every sampled R3 update while
    preserving the exact numerator sum_t pi_i^t(I)*sigma_i^t(I,a).
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
            matches = [
                action
                for action in game.actions(parent)
                if action.key() == remembered_key
            ]
            if len(matches) != 1:
                raise AssertionError(
                    "round-4 perfect recall must map to one predecessor action"
                )
            self.round4_parent[info] = (parent, matches[0])

        self.parent_segments: dict[TwoRoundInfoSet, list[_ParentSegment]] = {
            info: []
            for info in game.info_actions
            if info.round_index == 3
        }
        self.parent_segment_ends: dict[TwoRoundInfoSet, list[int]] = {
            info: [] for info in self.parent_segments
        }
        self.parent_active_since = {info: 1 for info in self.parent_segments}
        self.parent_cumulative = {
            info: {action: 0.0 for action in game.actions(info)}
            for info in self.parent_segments
        }

        self.r4_weighted_sum = {
            info: {action: 0.0 for action in actions}
            for info, actions in game.info_actions.items()
            if info.round_index == 4
        }
        self.r4_weighted_mass = {
            info: 0.0
            for info in self.r4_weighted_sum
        }
        self.r4_local_active_since = {
            info: 1
            for info in self.r4_weighted_sum
        }

    @staticmethod
    def _parent_info(info: TwoRoundInfoSet) -> TwoRoundInfoSet:
        if info.round_index != 4:
            raise ValueError("only round-4 infosets have predecessor relations")
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

    def _close_parent_segment(self, parent: TwoRoundInfoSet, end: int) -> None:
        start = self.parent_active_since[parent]
        if end < start:
            return
        distribution = self._distribution(parent)
        cumulative_before = dict(self.parent_cumulative[parent])
        segment = _ParentSegment(
            start=start,
            end=end,
            distribution=distribution,
            cumulative_before=cumulative_before,
        )
        self.parent_segments[parent].append(segment)
        self.parent_segment_ends[parent].append(end)
        length = end - start + 1
        cumulative = self.parent_cumulative[parent]
        for action, probability in distribution.items():
            cumulative[action] += length * probability
        self.parent_active_since[parent] = end + 1

    def _cumulative_parent_action_through(
        self,
        parent: TwoRoundInfoSet,
        action: NormalPlacementAction,
        iteration: int,
    ) -> float:
        if iteration <= 0:
            return 0.0
        segments = self.parent_segments[parent]
        ends = self.parent_segment_ends[parent]
        index = bisect_right(ends, iteration) - 1
        if index >= 0:
            segment = segments[index]
            cumulative = (
                segment.cumulative_before[action]
                + (segment.end - segment.start + 1)
                * segment.distribution[action]
            )
        else:
            cumulative = 0.0

        open_start = self.parent_active_since[parent]
        if iteration >= open_start:
            # All closed segments end before open_start. Add the still-active
            # parent strategy through the requested iteration.
            current = self._distribution(parent)
            cumulative = self.parent_cumulative[parent][action]
            cumulative += (iteration - open_start + 1) * current[action]
        elif index >= 0 and iteration < segments[index].end:
            # This path is relevant only for historical interval queries inside
            # a closed segment. Reconstruct from that segment's prefix.
            segment = segments[index]
            cumulative = segment.cumulative_before[action]
            if iteration >= segment.start:
                cumulative += (
                    iteration - segment.start + 1
                ) * segment.distribution[action]
        return cumulative

    def _parent_action_integral(
        self,
        parent: TwoRoundInfoSet,
        action: NormalPlacementAction,
        start: int,
        end: int,
    ) -> float:
        if end < start:
            return 0.0
        return (
            self._cumulative_parent_action_through(parent, action, end)
            - self._cumulative_parent_action_through(parent, action, start - 1)
        )

    def _flush_round4_average_through(
        self,
        info: TwoRoundInfoSet,
        end: int,
    ) -> None:
        start = self.r4_local_active_since[info]
        if end < start:
            return
        parent, parent_action = self.round4_parent[info]
        reach_integral = self._parent_action_integral(
            parent, parent_action, start, end
        )
        if reach_integral != 0.0:
            local = self._distribution(info)
            totals = self.r4_weighted_sum[info]
            for action, probability in local.items():
                totals[action] += reach_integral * probability
            self.r4_weighted_mass[info] += reach_integral
        self.r4_local_active_since[info] = end + 1

    def step(self) -> None:
        t = self.iteration + 1
        delta: dict[TwoRoundInfoSet, dict[NormalPlacementAction, float]] = {}
        self._sampled_traversal(0, delta)
        self._sampled_traversal(1, delta)
        changed = set(delta)

        # The pre-update strategies are the ones used in iteration t. Flush only
        # R4 infosets whose own local strategy is about to change.
        for info in changed:
            if info.round_index == 4:
                self._flush_round4_average_through(info, t)

        # Close only R3 predecessor segments whose own strategy is about to
        # change. No descendant scan is required.
        for info in changed:
            if info.round_index == 3:
                self._close_parent_segment(info, t)

        # Preserve the legacy local-time-average diagnostic from the base class.
        for info in changed:
            self._flush_local_strategy_used_through(info, t)

        for info, action_delta in delta.items():
            regrets = self.regrets[info]
            for action, increment in action_delta.items():
                regrets[action] += increment
            self.local_active_since[info] = t + 1
            if info.round_index == 4:
                self.r4_local_active_since[info] = t + 1
            elif info.round_index == 3:
                self.parent_active_since[info] = t + 1
        self.iteration = t

    def cfr_average_profile(self):
        if self.iteration == 0:
            return self.game.uniform_profile()

        local_time = self.behavioral_time_average_profile()
        profile = {}
        for info, actions in self.game.info_actions.items():
            if info.round_index == 3:
                profile[info] = local_time[info]
                continue

            totals = dict(self.r4_weighted_sum[info])
            mass = self.r4_weighted_mass[info]
            start = self.r4_local_active_since[info]
            if self.iteration >= start:
                parent, parent_action = self.round4_parent[info]
                reach_integral = self._parent_action_integral(
                    parent, parent_action, start, self.iteration
                )
                if reach_integral != 0.0:
                    local = self._distribution(info)
                    for action, probability in local.items():
                        totals[action] += reach_integral * probability
                    mass += reach_integral

            if mass <= 0.0:
                probability = 1.0 / len(actions)
                profile[info] = {action: probability for action in actions}
            else:
                profile[info] = {
                    action: totals[action] / mass for action in actions
                }
        return profile
