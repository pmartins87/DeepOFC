from __future__ import annotations

"""05F strategic comparator core for the hidden-discard-overlap fixture.

This module is intentionally independent of the UCT update statistics. It
materializes full finite-support information-set support, trains an external-
sampling MCCFR comparator, completes finite snapshots fail-closed, and computes
exact pure best responses on the reduced game.

Authority:
  HIDDEN_DISCARD_OVERLAP_STRATEGIC_COMPARATOR_REDUCED_GAME_ONLY
"""

from dataclasses import dataclass
import hashlib
import math
import random
from typing import Mapping, Sequence

from external_hidden_discard_overlap import OverlapSearchResult, OverlapWorld, validate_worlds, with_overlap_world
from strategic_cfr import HUState, child_state, information_state_key, legal_action_pairs, terminal_utility

AUTHORITY = "HIDDEN_DISCARD_OVERLAP_STRATEGIC_COMPARATOR_REDUCED_GAME_ONLY"
SCHEMA = "openofc-external-hidden-discard-overlap-strategic-v1"

BehaviorProfile = dict[str, dict[str, float]]
ReadOnlyProfile = Mapping[str, Mapping[str, float]]


@dataclass(frozen=True)
class ReachableSupport:
    information_state_key: str
    round_index: int
    actor: int
    action_keys: tuple[str, ...]
    concrete_states: tuple[HUState, ...]


@dataclass(frozen=True)
class MCCFRSnapshot:
    iterations: int
    information_states: int
    terminal_evaluations: int


@dataclass(frozen=True)
class CompletionReport:
    reachable_information_states: int
    base_information_states: int
    resolved_information_states: int
    iterations_per_missing_infoset: int
    profile: BehaviorProfile


@dataclass(frozen=True)
class ExactEvaluation:
    expected_u0: float
    terminal_leaves: int
    information_states_seen: int


@dataclass(frozen=True)
class ExactBestResponse:
    player: int
    value: float
    choices: tuple[tuple[str, str], ...]
    round3_infosets: int
    round4_infosets: int
    terminal_leaves: int

    def choice_map(self) -> dict[str, str]:
        return dict(self.choices)


@dataclass(frozen=True)
class ExactNashConv:
    nash_conv: float
    exploitability: float
    br0: ExactBestResponse
    br1: ExactBestResponse


def _uniform(action_keys: Sequence[str]) -> dict[str, float]:
    keys = tuple(action_keys)
    if not keys:
        raise ValueError("cannot build distribution over no actions")
    p = 1.0 / len(keys)
    return {key: p for key in keys}


def _distribution(
    profile: ReadOnlyProfile,
    info_key: str,
    action_keys: Sequence[str],
    *,
    allow_missing_uniform: bool,
) -> dict[str, float]:
    legal = tuple(action_keys)
    supplied = profile.get(info_key)
    if supplied is None:
        if allow_missing_uniform:
            return _uniform(legal)
        raise ValueError(f"explicit profile missing infoset: {info_key}")
    illegal = set(supplied) - set(legal)
    if illegal:
        raise ValueError(f"profile contains illegal actions: {sorted(illegal)}")
    weights = {}
    for key in legal:
        value = float(supplied.get(key, 0.0))
        if value < 0.0 or not math.isfinite(value):
            raise ValueError("profile probabilities must be finite and non-negative")
        weights[key] = value
    mass = sum(weights.values())
    if mass <= 0.0:
        if allow_missing_uniform:
            return _uniform(legal)
        raise ValueError("explicit profile has zero legal probability mass")
    return {key: value / mass for key, value in weights.items()}


def visit_profile_from_overlap_search(result: OverlapSearchResult) -> BehaviorProfile:
    profile: BehaviorProfile = {}
    for row in result.node_stats:
        total = sum(visits for _key, visits in row.action_visits)
        action_keys = tuple(key for key, _visits in row.action_visits)
        profile[row.information_state_key] = (
            _uniform(action_keys)
            if total <= 0
            else {key: visits / total for key, visits in row.action_visits}
        )
    return profile


def build_reachable_support(base_state: HUState, worlds: Sequence[OverlapWorld]) -> tuple[ReachableSupport, ...]:
    support = validate_worlds(worlds)
    grouped: dict[str, dict[str, HUState]] = {}
    metadata: dict[str, tuple[int, int, tuple[str, ...]]] = {}

    def walk(state: HUState) -> None:
        if state.terminal():
            return
        info_key = information_state_key(state)
        pairs = tuple(legal_action_pairs(state))
        action_keys = tuple(key for key, _action in pairs)
        meta = (state.round_index, state.actor, action_keys)
        previous = metadata.get(info_key)
        if previous is None:
            metadata[info_key] = meta
        elif previous != meta:
            raise AssertionError("infoset collided across actor/round/action-set")
        grouped.setdefault(info_key, {})[repr(state)] = state
        for _key, action in pairs:
            walk(child_state(state, action))

    for world in support:
        walk(with_overlap_world(base_state, world))

    rows = []
    for info_key in sorted(grouped):
        round_index, actor, action_keys = metadata[info_key]
        concrete = tuple(grouped[info_key][fingerprint] for fingerprint in sorted(grouped[info_key]))
        rows.append(ReachableSupport(info_key, round_index, actor, action_keys, concrete))
    return tuple(rows)


class OverlapExternalSamplingMCCFR:
    def __init__(self, base_state: HUState, worlds: Sequence[OverlapWorld], *, seed: int) -> None:
        self.base_state = base_state
        self.worlds = validate_worlds(worlds)
        self.rng = random.Random(int(seed))
        self.regrets: dict[str, dict[str, float]] = {}
        self.action_sets: dict[str, tuple[str, ...]] = {}
        self.iterations = 0
        self.terminal_evaluations = 0

    def _ensure(self, state: HUState) -> tuple[str, tuple[tuple[str, object], ...]]:
        info_key = information_state_key(state)
        pairs = tuple(legal_action_pairs(state))
        keys = tuple(key for key, _action in pairs)
        previous = self.action_sets.get(info_key)
        if previous is None:
            self.action_sets[info_key] = keys
            self.regrets[info_key] = {key: 0.0 for key in keys}
        elif previous != keys:
            raise AssertionError("same infoset produced different action set")
        return info_key, pairs

    def _policy(self, info_key: str) -> dict[str, float]:
        keys = self.action_sets[info_key]
        positive = {key: max(0.0, self.regrets[info_key][key]) for key in keys}
        total = sum(positive.values())
        return _uniform(keys) if total <= 0.0 else {key: value / total for key, value in positive.items()}

    def _sample(self, distribution: Mapping[str, float], action_keys: Sequence[str]) -> str:
        x = self.rng.random()
        cumulative = 0.0
        last = None
        for key in action_keys:
            last = key
            cumulative += distribution[key]
            if x <= cumulative:
                return key
        if last is None:
            raise RuntimeError("cannot sample empty distribution")
        return last

    def _traverse(self, state: HUState, traverser: int, delta: dict[str, dict[str, float]]) -> float:
        if state.terminal():
            self.terminal_evaluations += 1
            u0 = float(terminal_utility(state, 0))
            return u0 if traverser == 0 else -u0
        info_key, pairs = self._ensure(state)
        keys = self.action_sets[info_key]
        policy = self._policy(info_key)
        by_key = dict(pairs)
        if state.actor != traverser:
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

    def step(self) -> None:
        world = self.worlds[self.rng.randrange(len(self.worlds))]
        state = with_overlap_world(self.base_state, world)
        delta: dict[str, dict[str, float]] = {}
        self._traverse(state, 0, delta)
        self._traverse(state, 1, delta)
        for info_key, increments in delta.items():
            for action_key, increment in increments.items():
                self.regrets[info_key][action_key] += increment
        self.iterations += 1

    def run(self, iterations: int) -> None:
        if iterations < 0:
            raise ValueError("iterations must be non-negative")
        for _ in range(iterations):
            self.step()

    def current_profile(self) -> BehaviorProfile:
        return {info_key: self._policy(info_key) for info_key in sorted(self.action_sets)}

    def snapshot(self) -> MCCFRSnapshot:
        return MCCFRSnapshot(self.iterations, len(self.action_sets), self.terminal_evaluations)


def _derived_seed(base_seed: int, info_key: str) -> int:
    digest = hashlib.sha256(f"{int(base_seed)}|{info_key}".encode()).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


class _LocalBandit:
    def __init__(self, keys: Sequence[str]) -> None:
        self.keys = tuple(keys)
        self.visits = {key: 0 for key in self.keys}
        self.sums = {key: 0.0 for key in self.keys}
        self.total = 0

    def select(self, maximize: bool, exploration: float) -> str:
        unseen = [key for key in self.keys if self.visits[key] == 0]
        if unseen:
            return unseen[0]
        log_total = math.log(self.total + 1.0)
        score = lambda key: self.sums[key] / self.visits[key]
        if maximize:
            return max(self.keys, key=lambda key: (score(key) + exploration * math.sqrt(log_total / self.visits[key]), -self.keys.index(key)))
        return min(self.keys, key=lambda key: (score(key) - exploration * math.sqrt(log_total / self.visits[key]), self.keys.index(key)))

    def observe(self, key: str, value: float) -> None:
        self.visits[key] += 1
        self.sums[key] += float(value)
        self.total += 1


def complete_profile(
    base_profile: ReadOnlyProfile,
    support_rows: Sequence[ReachableSupport],
    *,
    iterations_per_missing_infoset: int,
    seed: int,
    exploration: float = 1.0,
) -> CompletionReport:
    if not support_rows:
        raise ValueError("completion requires support rows")
    max_actions = max(len(row.action_keys) for row in support_rows)
    if iterations_per_missing_infoset < max_actions:
        raise ValueError("completion budget must visit every local action")
    reachable = {row.information_state_key for row in support_rows}
    frozen: BehaviorProfile = {
        key: {action: float(probability) for action, probability in dist.items()}
        for key, dist in base_profile.items()
    }
    completed: BehaviorProfile = {}
    for row in support_rows:
        if row.information_state_key in frozen:
            completed[row.information_state_key] = _distribution(
                frozen, row.information_state_key, row.action_keys, allow_missing_uniform=False
            )
    base_count = len(completed)

    def sample_action(dist: Mapping[str, float], keys: Sequence[str], rng: random.Random) -> str:
        x = rng.random()
        cumulative = 0.0
        last = None
        for key in keys:
            last = key
            cumulative += dist[key]
            if x <= cumulative:
                return key
        assert last is not None
        return last

    # Every missing resolver sees the same immutable frozen base snapshot. Newly
    # generated local decisions never bootstrap one another in this pass.
    for row in support_rows:
        if row.information_state_key in completed:
            continue
        rng = random.Random(_derived_seed(seed, row.information_state_key))
        bandit = _LocalBandit(row.action_keys)
        for _ in range(iterations_per_missing_infoset):
            root_action_key = bandit.select(row.actor == 0, exploration)
            state = row.concrete_states[rng.randrange(len(row.concrete_states))]
            root_action = dict(legal_action_pairs(state))[root_action_key]
            state = child_state(state, root_action)
            while not state.terminal():
                key = information_state_key(state)
                pairs = tuple(legal_action_pairs(state))
                keys = tuple(action_key for action_key, _action in pairs)
                dist = _distribution(frozen, key, keys, allow_missing_uniform=True)
                selected = sample_action(dist, keys, rng)
                state = child_state(state, dict(pairs)[selected])
            bandit.observe(root_action_key, float(terminal_utility(state, 0)))
        completed[row.information_state_key] = {
            key: bandit.visits[key] / bandit.total for key in row.action_keys
        }

    if set(completed) != reachable:
        raise AssertionError("completion failed to materialize all reachable infosets")
    return CompletionReport(
        reachable_information_states=len(support_rows),
        base_information_states=base_count,
        resolved_information_states=len(support_rows) - base_count,
        iterations_per_missing_infoset=iterations_per_missing_infoset,
        profile=completed,
    )


def exact_profile_value(
    base_state: HUState,
    worlds: Sequence[OverlapWorld],
    *,
    profile: ReadOnlyProfile,
    support_rows: Sequence[ReachableSupport],
) -> ExactEvaluation:
    expected = {row.information_state_key for row in support_rows}
    missing = expected - set(profile)
    if missing:
        raise ValueError(f"strict evaluation refuses missing infosets: {len(missing)}")
    terminal_leaves = 0
    seen: set[str] = set()

    def walk(state: HUState) -> float:
        nonlocal terminal_leaves
        if state.terminal():
            terminal_leaves += 1
            return float(terminal_utility(state, 0))
        key = information_state_key(state)
        seen.add(key)
        pairs = tuple(legal_action_pairs(state))
        keys = tuple(action_key for action_key, _action in pairs)
        dist = _distribution(profile, key, keys, allow_missing_uniform=False)
        by_key = dict(pairs)
        return sum(dist[action_key] * walk(child_state(state, by_key[action_key])) for action_key in keys if dist[action_key] > 0.0)

    support = validate_worlds(worlds)
    total = sum(walk(with_overlap_world(base_state, world)) for world in support)
    return ExactEvaluation(total / len(support), terminal_leaves, len(seen))


def exact_best_response(
    base_state: HUState,
    worlds: Sequence[OverlapWorld],
    *,
    opponent_profile: ReadOnlyProfile,
    player: int,
    support_rows: Sequence[ReachableSupport],
) -> ExactBestResponse:
    if player not in (0, 1):
        raise ValueError("player must be 0 or 1")
    support = validate_worlds(worlds)
    expected_opponent = {row.information_state_key for row in support_rows if row.actor != player}
    missing = expected_opponent - set(opponent_profile)
    if missing:
        raise ValueError(f"exact BR opponent profile incomplete: {len(missing)}")

    action_sets: dict[str, tuple[str, ...]] = {}
    round4_values: dict[str, dict[str, float]] = {}
    round4_parent: dict[str, tuple[str, str]] = {}
    terminal_leaves = 0
    chance = 1.0 / len(support)

    def remember(state: HUState) -> tuple[str, tuple[tuple[str, object], ...]]:
        key = information_state_key(state)
        pairs = tuple(legal_action_pairs(state))
        keys = tuple(action_key for action_key, _action in pairs)
        previous = action_sets.get(key)
        if previous is None:
            action_sets[key] = keys
        elif previous != keys:
            raise AssertionError("same infoset produced different legal actions")
        return key, pairs

    def walk(state: HUState, opp_reach: float, r3_info: str | None, r3_action: str | None, r4_info: str | None, r4_action: str | None) -> None:
        nonlocal terminal_leaves
        if state.terminal():
            terminal_leaves += 1
            if None in (r3_info, r3_action, r4_info, r4_action):
                raise AssertionError("BR terminal missing responder decisions")
            utility = float(terminal_utility(state, player))
            bucket = round4_values.setdefault(r4_info, {key: 0.0 for key in action_sets[r4_info]})  # type: ignore[index]
            bucket[r4_action] += chance * opp_reach * utility  # type: ignore[index]
            parent = (r3_info, r3_action)  # type: ignore[arg-type]
            previous = round4_parent.setdefault(r4_info, parent)  # type: ignore[arg-type]
            if previous != parent:
                raise AssertionError("perfect-recall parent mismatch")
            return
        key, pairs = remember(state)
        keys = action_sets[key]
        by_key = dict(pairs)
        if state.actor == player:
            for action_key in keys:
                if state.round_index == 3:
                    walk(child_state(state, by_key[action_key]), opp_reach, key, action_key, r4_info, r4_action)
                elif state.round_index == 4:
                    if r3_info is None or r3_action is None:
                        raise AssertionError("R4 responder state lacks R3 predecessor")
                    walk(child_state(state, by_key[action_key]), opp_reach, r3_info, r3_action, key, action_key)
                else:
                    raise AssertionError("05F responder should act only on R3/R4")
            return
        dist = _distribution(opponent_profile, key, keys, allow_missing_uniform=False)
        for action_key in keys:
            walk(child_state(state, by_key[action_key]), opp_reach * dist[action_key], r3_info, r3_action, r4_info, r4_action)

    for world in support:
        walk(with_overlap_world(base_state, world), 1.0, None, None, None, None)

    expected_r3 = {row.information_state_key for row in support_rows if row.actor == player and row.round_index == 3}
    expected_r4 = {row.information_state_key for row in support_rows if row.actor == player and row.round_index == 4}
    round3_values = {key: {action: 0.0 for action in action_sets[key]} for key in expected_r3}
    round4_choices = {}
    for key in sorted(expected_r4):
        values = round4_values[key]
        best = min(values, key=lambda action: (-values[action], action))
        round4_choices[key] = best
        parent_info, parent_action = round4_parent[key]
        round3_values[parent_info][parent_action] += values[best]
    round3_choices = {}
    total = 0.0
    for key in sorted(expected_r3):
        values = round3_values[key]
        best = min(values, key=lambda action: (-values[action], action))
        round3_choices[key] = best
        total += values[best]
    choices = {**round3_choices, **round4_choices}
    expected_own = {row.information_state_key for row in support_rows if row.actor == player}
    if set(choices) != expected_own:
        raise AssertionError("exact BR did not cover every responder infoset")
    return ExactBestResponse(
        player=player,
        value=total,
        choices=tuple(sorted(choices.items())),
        round3_infosets=len(round3_choices),
        round4_infosets=len(round4_choices),
        terminal_leaves=terminal_leaves,
    )


def exact_nash_conv(
    base_state: HUState,
    worlds: Sequence[OverlapWorld],
    *,
    profile: ReadOnlyProfile,
    support_rows: Sequence[ReachableSupport],
) -> ExactNashConv:
    br0 = exact_best_response(base_state, worlds, opponent_profile=profile, player=0, support_rows=support_rows)
    br1 = exact_best_response(base_state, worlds, opponent_profile=profile, player=1, support_rows=support_rows)
    nash_conv = br0.value + br1.value
    if nash_conv < -1e-9:
        raise AssertionError(f"negative zero-sum NashConv: {nash_conv}")
    return ExactNashConv(max(0.0, nash_conv), max(0.0, nash_conv / 2.0), br0, br1)


__all__ = [
    "AUTHORITY", "SCHEMA", "BehaviorProfile", "ReachableSupport", "MCCFRSnapshot",
    "CompletionReport", "ExactEvaluation", "ExactBestResponse", "ExactNashConv",
    "visit_profile_from_overlap_search", "build_reachable_support",
    "OverlapExternalSamplingMCCFR", "complete_profile", "exact_profile_value",
    "exact_best_response", "exact_nash_conv",
]
