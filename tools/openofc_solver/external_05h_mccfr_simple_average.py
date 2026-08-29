from __future__ import annotations

"""External-sampling MCCFR with an additive SIMPLE average-policy accumulator.

The regret/current-policy dynamics deliberately mirror
`OverlapExternalSamplingMCCFR` exactly.  The only added state is a cumulative
behavior-policy sum at opponent information sets encountered during the other
player's traversal, matching the two-player SIMPLE averaging pattern used by
OpenSpiel's external-sampling MCCFR.

This module is shadow research only.  It does not alter the existing solver or
its frozen 05G/05H current-policy experiments.
"""

from dataclasses import dataclass
from typing import Mapping

from external_hidden_discard_overlap_strategic import (
    BehaviorProfile,
    OverlapExternalSamplingMCCFR,
)
from strategic_cfr import HUState, child_state, terminal_utility

AUTHORITY = "BROADER_HIDDEN_INFORMATION_REDUCED_GAME_SHADOW_ONLY"
SCHEMA = "openofc-external-mccfr-simple-average-v1"
AVERAGE_TYPE = "EXTERNAL_SAMPLING_SIMPLE_AVERAGE_TWO_PLAYER"


@dataclass(frozen=True)
class AverageSnapshot:
    iterations: int
    regret_information_states: int
    average_information_states: int
    terminal_evaluations: int
    average_policy_updates: int


class OverlapExternalSamplingMCCFRSimpleAverage(OverlapExternalSamplingMCCFR):
    """Preserve base regret dynamics while accumulating a simple average policy."""

    def __init__(self, base_state, worlds, *, seed: int) -> None:
        super().__init__(base_state, worlds, seed=seed)
        self.average_sums: dict[str, dict[str, float]] = {}
        self.average_policy_updates = 0

    def _accumulate_simple_average(
        self,
        info_key: str,
        policy: Mapping[str, float],
    ) -> None:
        keys = self.action_sets[info_key]
        bucket = self.average_sums.setdefault(info_key, {key: 0.0 for key in keys})
        if tuple(bucket) != keys:
            raise AssertionError("average-policy action set changed for one infoset")
        for key in keys:
            bucket[key] += float(policy[key])
        self.average_policy_updates += 1

    def _traverse(self, state: HUState, traverser: int, delta: dict[str, dict[str, float]]) -> float:
        # This method intentionally copies the parent traversal control flow.
        # No additional RNG calls are introduced, so current-policy/regret
        # trajectories remain byte-for-byte reproducible for a fixed seed.
        if state.terminal():
            self.terminal_evaluations += 1
            u0 = float(terminal_utility(state, 0))
            return u0 if traverser == 0 else -u0

        info_key, pairs = self._ensure(state)
        keys = self.action_sets[info_key]
        policy = self._policy(info_key)
        by_key = dict(pairs)

        if state.actor != traverser:
            # Two-player external-sampling SIMPLE average: when traversing one
            # player, accumulate the current policy at the opponent node that
            # is actually visited before sampling that opponent action.
            self._accumulate_simple_average(info_key, policy)
            selected = self._sample(policy, keys)
            return self._traverse(child_state(state, by_key[selected]), traverser, delta)

        values = {}
        node_value = 0.0
        for key in keys:
            value = self._traverse(child_state(state, by_key[key]), traverser, delta)
            values[key] = value
            node_value += policy[key] * value
        bucket = delta.setdefault(info_key, {key: 0.0 for key in keys})
        for key in keys:
            bucket[key] += values[key] - node_value
        return node_value

    def average_profile(self) -> BehaviorProfile:
        profile: BehaviorProfile = {}
        for info_key in sorted(self.average_sums):
            keys = self.action_sets[info_key]
            bucket = self.average_sums[info_key]
            total = sum(float(bucket[key]) for key in keys)
            if total <= 0.0:
                raise AssertionError("materialized average infoset has zero cumulative policy mass")
            profile[info_key] = {key: float(bucket[key]) / total for key in keys}
        return profile

    def average_snapshot(self) -> AverageSnapshot:
        return AverageSnapshot(
            iterations=self.iterations,
            regret_information_states=len(self.action_sets),
            average_information_states=len(self.average_sums),
            terminal_evaluations=self.terminal_evaluations,
            average_policy_updates=self.average_policy_updates,
        )


__all__ = [
    "AUTHORITY",
    "SCHEMA",
    "AVERAGE_TYPE",
    "AverageSnapshot",
    "OverlapExternalSamplingMCCFRSimpleAverage",
]
