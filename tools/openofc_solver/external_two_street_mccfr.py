from __future__ import annotations

"""Independent external-sampling MCCFR comparator for the 05C reduced game.

This module deliberately reuses only the canonical game transitions and frozen
physical-world support. It does not reuse UCT statistics to update regrets.

Authority:
  REDUCED_GAME_STRATEGIC_COMPARATOR_NOT_CERTIFICATION
"""

from dataclasses import dataclass
import math
import random
from typing import Iterable, Mapping, Sequence

from external_two_street_infoset_search import (
    TwoStreetSearchResult,
    TwoStreetWorld,
    _assert_root_isolation,
    _with_world,
)
from strategic_cfr import HUState, child_state, information_state_key, legal_action_pairs, terminal_utility

AUTHORITY = "REDUCED_GAME_STRATEGIC_COMPARATOR_NOT_CERTIFICATION"
SCHEMA = "openofc-external-two-street-mccfr-v1"

BehaviorProfile = dict[str, dict[str, float]]
ReadOnlyProfile = Mapping[str, Mapping[str, float]]


@dataclass(frozen=True)
class ExactProfileEvaluation:
    expected_u0: float
    terminal_leaves: int
    information_states_seen: int
    support_worlds: int


@dataclass(frozen=True)
class MCCFRTrainingSnapshot:
    iteration: int
    information_states: int
    terminal_evaluations: int
    root_information_state_key: str


def _uniform(action_keys: Sequence[str]) -> dict[str, float]:
    keys = tuple(action_keys)
    if not keys:
        raise ValueError("cannot build a distribution over no actions")
    p = 1.0 / len(keys)
    return {key: p for key in keys}


def _profile_distribution(
    profile: ReadOnlyProfile,
    info_key: str,
    action_keys: Sequence[str],
) -> dict[str, float]:
    legal = tuple(action_keys)
    supplied = profile.get(info_key)
    if supplied is None:
        return _uniform(legal)
    illegal = set(supplied) - set(legal)
    if illegal:
        raise ValueError(f"profile contains illegal actions at info set: {sorted(illegal)}")
    weights = {}
    for key in legal:
        value = float(supplied.get(key, 0.0))
        if value < 0.0 or not math.isfinite(value):
            raise ValueError("profile probabilities must be finite and non-negative")
        weights[key] = value
    mass = sum(weights.values())
    if mass <= 0.0:
        return _uniform(legal)
    return {key: value / mass for key, value in weights.items()}


def visit_profile_from_search(result: TwoStreetSearchResult) -> BehaviorProfile:
    """Extract the declared 05D search policy: local action-visit frequencies."""
    profile: BehaviorProfile = {}
    for node in result.node_stats:
        action_keys = tuple(stat.action_key for stat in node.action_stats)
        total = sum(stat.visits for stat in node.action_stats)
        if total <= 0:
            profile[node.information_state_key] = _uniform(action_keys)
        else:
            profile[node.information_state_key] = {
                stat.action_key: stat.visits / total for stat in node.action_stats
            }
    return profile


def exact_profile_value(
    base_state: HUState,
    worlds: Iterable[TwoStreetWorld],
    *,
    p0_profile: ReadOnlyProfile,
    p1_profile: ReadOnlyProfile,
) -> ExactProfileEvaluation:
    """Exactly enumerate a fixed pair of behavioral profiles on finite support.

    Missing information states use an explicit uniform fallback. This function
    evaluates a fixed profile pair only; it is not a best-response oracle.
    """
    support = tuple(worlds)
    if len(support) < 2:
        raise ValueError("exact profile evaluation requires at least two support worlds")
    _assert_root_isolation(base_state, support)
    terminal_leaves = 0
    infosets: set[str] = set()

    def walk(state: HUState) -> float:
        nonlocal terminal_leaves
        if state.terminal():
            terminal_leaves += 1
            return float(terminal_utility(state, 0))
        info_key = information_state_key(state)
        infosets.add(info_key)
        pairs = legal_action_pairs(state)
        action_keys = tuple(key for key, _action in pairs)
        profile = p0_profile if state.actor == 0 else p1_profile
        distribution = _profile_distribution(profile, info_key, action_keys)
        by_key = dict(pairs)
        value = 0.0
        for action_key in action_keys:
            probability = distribution[action_key]
            if probability <= 0.0:
                continue
            value += probability * walk(child_state(state, by_key[action_key]))
        return value

    total = 0.0
    for world in support:
        total += walk(_with_world(base_state, world))
    return ExactProfileEvaluation(
        expected_u0=total / len(support),
        terminal_leaves=terminal_leaves,
        information_states_seen=len(infosets),
        support_worlds=len(support),
    )


class TwoStreetExternalSamplingMCCFR:
    """External-sampling MCCFR current-profile comparator.

    One global iteration samples one complete physical world and performs one
    traversal for each player against the same pre-update regret tables. At the
    traverser's nodes all actions are enumerated; at the opponent's nodes one
    action is sampled from current regret matching.

    Q0 intentionally exposes only the *current* regret-matching profile. No
    local time average is mislabeled as a CFR average.
    """

    def __init__(
        self,
        base_state: HUState,
        worlds: Iterable[TwoStreetWorld],
        *,
        seed: int,
    ) -> None:
        self.base_state = base_state
        self.worlds = tuple(worlds)
        if len(self.worlds) < 2:
            raise ValueError("MCCFR requires at least two support worlds")
        self.root_information_state_key = _assert_root_isolation(base_state, self.worlds)
        self.rng = random.Random(int(seed))
        self.seed = int(seed)
        self.iteration = 0
        self.terminal_evaluations = 0
        self.regrets: dict[str, dict[str, float]] = {}
        self.action_sets: dict[str, tuple[str, ...]] = {}

    def _ensure_node(self, state: HUState) -> tuple[str, tuple[tuple[str, object], ...]]:
        info_key = information_state_key(state)
        pairs = tuple(legal_action_pairs(state))
        action_keys = tuple(key for key, _action in pairs)
        existing = self.action_sets.get(info_key)
        if existing is None:
            self.action_sets[info_key] = action_keys
            self.regrets[info_key] = {key: 0.0 for key in action_keys}
        elif existing != action_keys:
            raise AssertionError("same information state produced a different action set")
        return info_key, pairs

    def _distribution(self, info_key: str) -> dict[str, float]:
        action_keys = self.action_sets[info_key]
        regrets = self.regrets[info_key]
        positive = {key: max(0.0, regrets[key]) for key in action_keys}
        total = sum(positive.values())
        if total <= 0.0:
            return _uniform(action_keys)
        return {key: positive[key] / total for key in action_keys}

    def _sample_action(self, distribution: Mapping[str, float], action_keys: Sequence[str]) -> str:
        threshold = self.rng.random()
        cumulative = 0.0
        last = None
        for key in action_keys:
            last = key
            cumulative += distribution[key]
            if threshold <= cumulative:
                return key
        if last is None:
            raise RuntimeError("cannot sample from an empty distribution")
        return last

    @staticmethod
    def _own_utility(u0: float, traverser: int) -> float:
        return u0 if traverser == 0 else -u0

    def _traverse(
        self,
        state: HUState,
        traverser: int,
        delta: dict[str, dict[str, float]],
    ) -> float:
        if state.terminal():
            self.terminal_evaluations += 1
            return self._own_utility(float(terminal_utility(state, 0)), traverser)

        info_key, pairs = self._ensure_node(state)
        action_keys = self.action_sets[info_key]
        distribution = self._distribution(info_key)
        by_key = dict(pairs)

        if state.actor != traverser:
            sampled = self._sample_action(distribution, action_keys)
            return self._traverse(child_state(state, by_key[sampled]), traverser, delta)

        action_values: dict[str, float] = {}
        node_value = 0.0
        for action_key in action_keys:
            value = self._traverse(child_state(state, by_key[action_key]), traverser, delta)
            action_values[action_key] = value
            node_value += distribution[action_key] * value
        bucket = delta.setdefault(info_key, {key: 0.0 for key in action_keys})
        for action_key, value in action_values.items():
            bucket[action_key] += value - node_value
        return node_value

    def step(self) -> None:
        world = self.worlds[self.rng.randrange(len(self.worlds))]
        state = _with_world(self.base_state, world)
        delta: dict[str, dict[str, float]] = {}
        self._traverse(state, 0, delta)
        self._traverse(state, 1, delta)
        for info_key, increments in delta.items():
            regrets = self.regrets[info_key]
            for action_key, increment in increments.items():
                regrets[action_key] += increment
        self.iteration += 1

    def run(self, iterations: int) -> None:
        if iterations < 0:
            raise ValueError("iterations must be non-negative")
        for _ in range(iterations):
            self.step()

    def current_profile(self) -> BehaviorProfile:
        return {
            info_key: self._distribution(info_key)
            for info_key in sorted(self.action_sets)
        }

    def snapshot(self) -> MCCFRTrainingSnapshot:
        return MCCFRTrainingSnapshot(
            iteration=self.iteration,
            information_states=len(self.action_sets),
            terminal_evaluations=self.terminal_evaluations,
            root_information_state_key=self.root_information_state_key,
        )


def root_total_variation(
    base_state: HUState,
    p: ReadOnlyProfile,
    q: ReadOnlyProfile,
) -> float:
    info_key = information_state_key(base_state)
    action_keys = tuple(key for key, _action in legal_action_pairs(base_state))
    pd = _profile_distribution(p, info_key, action_keys)
    qd = _profile_distribution(q, info_key, action_keys)
    return 0.5 * sum(abs(pd[key] - qd[key]) for key in action_keys)


__all__ = [
    "AUTHORITY",
    "SCHEMA",
    "BehaviorProfile",
    "ExactProfileEvaluation",
    "MCCFRTrainingSnapshot",
    "TwoStreetExternalSamplingMCCFR",
    "exact_profile_value",
    "visit_profile_from_search",
    "root_total_variation",
]
