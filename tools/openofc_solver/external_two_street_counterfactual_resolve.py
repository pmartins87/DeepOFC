from __future__ import annotations

"""Counterfactual information-set policy completion for the 05D reduced game.

The 05D-Q0 comparison exposed a mechanical asymmetry: a finite-trajectory UCT
snapshot covered only the information sets it happened to visit, while exact
cross-profile evaluation can reach additional information sets after an
opponent deviation.  Falling back to a uniform policy at those states makes the
comparison partly a test of the fallback rather than of the search policy.

This module supplies a deliberately limited research remedy.  It first
materializes the complete set of information states reachable on the frozen
finite physical-world support.  Missing local policies are then resolved with a
fresh root bandit whose action is chosen *before* a compatible physical state is
sampled.  Downstream actions follow the frozen base profile; any downstream
state that was itself absent from that base profile uses an explicit uniform
rollout policy.  Thus completion is order-independent and cannot bootstrap from
its own newly generated decisions.

The completed policy is a shadow research policy only.  Uniform weighting over
compatible concrete states is a finite-support search prior, not a proved
Bayesian posterior or equilibrium belief.  No exploitability or certification
authority is created here.

Authority:
  COUNTERFACTUAL_INFOSET_COMPLETION_SHADOW_ONLY
"""

from dataclasses import dataclass
import hashlib
import math
import random
from typing import Iterable, Mapping, Sequence

from external_two_street_infoset_search import TwoStreetWorld, _assert_root_isolation, _with_world
from external_two_street_mccfr import BehaviorProfile, ExactProfileEvaluation, ReadOnlyProfile, exact_profile_value
from strategic_cfr import HUState, child_state, information_state_key, legal_action_pairs, terminal_utility

AUTHORITY = "COUNTERFACTUAL_INFOSET_COMPLETION_SHADOW_ONLY"
SCHEMA = "openofc-external-two-street-counterfactual-completion-v1"


@dataclass(frozen=True)
class ReachableInfoSetSupport:
    information_state_key: str
    round_index: int
    actor: int
    action_keys: tuple[str, ...]
    concrete_states: tuple[HUState, ...]


@dataclass(frozen=True)
class LocalResolveResult:
    information_state_key: str
    actor: int
    iterations: int
    compatible_states: int
    action_visits: tuple[tuple[str, int], ...]
    action_mean_u0: tuple[tuple[str, float], ...]
    distribution: tuple[tuple[str, float], ...]


@dataclass(frozen=True)
class CompletionReport:
    authority: str
    reachable_information_states: int
    base_information_states_on_support: int
    resolved_information_states: int
    completed_information_states: int
    p0_information_states: int
    p1_information_states: int
    iterations_per_resolved_infoset: int
    seed: int
    exploration: float
    profile: BehaviorProfile


class _LocalBandit:
    def __init__(self, action_keys: Sequence[str]) -> None:
        keys = tuple(action_keys)
        if not keys:
            raise ValueError("local resolver requires at least one action")
        self.action_keys = keys
        self.visits = {key: 0 for key in keys}
        self.sums = {key: 0.0 for key in keys}
        self.total_visits = 0

    def observe(self, action_key: str, value: float) -> None:
        self.visits[action_key] += 1
        self.sums[action_key] += float(value)
        self.total_visits += 1

    def _mean(self, action_key: str) -> float:
        visits = self.visits[action_key]
        if visits <= 0:
            raise ValueError("mean requested for unvisited local action")
        return self.sums[action_key] / visits

    def select(self, *, maximize: bool, exploration: float) -> str:
        unvisited = [key for key in self.action_keys if self.visits[key] == 0]
        if unvisited:
            return unvisited[0]
        log_total = math.log(self.total_visits + 1.0)
        if maximize:
            return max(
                self.action_keys,
                key=lambda key: (
                    self._mean(key) + exploration * math.sqrt(log_total / self.visits[key]),
                    -self.action_keys.index(key),
                ),
            )
        return min(
            self.action_keys,
            key=lambda key: (
                self._mean(key) - exploration * math.sqrt(log_total / self.visits[key]),
                self.action_keys.index(key),
            ),
        )


def _normalize_distribution(
    profile: ReadOnlyProfile,
    info_key: str,
    action_keys: Sequence[str],
) -> dict[str, float]:
    legal = tuple(action_keys)
    supplied = profile.get(info_key)
    if supplied is None:
        probability = 1.0 / len(legal)
        return {key: probability for key in legal}
    illegal = set(supplied) - set(legal)
    if illegal:
        raise ValueError(f"profile contains illegal actions at info set: {sorted(illegal)}")
    weights: dict[str, float] = {}
    for key in legal:
        value = float(supplied.get(key, 0.0))
        if value < 0.0 or not math.isfinite(value):
            raise ValueError("profile probabilities must be finite and non-negative")
        weights[key] = value
    mass = sum(weights.values())
    if mass <= 0.0:
        probability = 1.0 / len(legal)
        return {key: probability for key in legal}
    return {key: value / mass for key, value in weights.items()}


def _sample_action(
    distribution: Mapping[str, float],
    action_keys: Sequence[str],
    rng: random.Random,
) -> str:
    threshold = rng.random()
    cumulative = 0.0
    last: str | None = None
    for key in action_keys:
        last = key
        cumulative += distribution[key]
        if threshold <= cumulative:
            return key
    if last is None:
        raise RuntimeError("cannot sample an empty action distribution")
    return last


def build_reachable_infoset_support(
    base_state: HUState,
    worlds: Iterable[TwoStreetWorld],
) -> tuple[ReachableInfoSetSupport, ...]:
    """Enumerate every information state reachable on the frozen finite support.

    Concrete states are grouped by canonical information-state key.  The group
    retains hidden physical states only as an internal support for a root-blind
    local resolver; those hidden cards never become part of the policy key.
    """
    support = tuple(worlds)
    if len(support) < 2:
        raise ValueError("reachable-support enumeration requires at least two worlds")
    _assert_root_isolation(base_state, support)

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
            raise AssertionError("information-state key collided across actor/round/action-set")
        # repr(state) includes the complete physical deal and public history and
        # is used only to deduplicate identical concrete states deterministically.
        grouped.setdefault(info_key, {})[repr(state)] = state
        for _key, action in pairs:
            walk(child_state(state, action))

    for world in support:
        walk(_with_world(base_state, world))

    rows: list[ReachableInfoSetSupport] = []
    for info_key in sorted(grouped):
        round_index, actor, action_keys = metadata[info_key]
        states = tuple(grouped[info_key][fingerprint] for fingerprint in sorted(grouped[info_key]))
        rows.append(
            ReachableInfoSetSupport(
                information_state_key=info_key,
                round_index=round_index,
                actor=actor,
                action_keys=action_keys,
                concrete_states=states,
            )
        )
    return tuple(rows)


def _derived_seed(base_seed: int, info_key: str) -> int:
    digest = hashlib.sha256(f"{int(base_seed)}|{info_key}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def resolve_missing_infoset(
    support: ReachableInfoSetSupport,
    *,
    frozen_p0_profile: ReadOnlyProfile,
    frozen_p1_profile: ReadOnlyProfile,
    iterations: int,
    seed: int,
    exploration: float = 1.0,
) -> LocalResolveResult:
    """Resolve one information set without conditioning the root on hidden cards."""
    if iterations < len(support.action_keys):
        raise ValueError("local resolver iterations must cover every legal root action at least once")
    if exploration < 0.0 or not math.isfinite(exploration):
        raise ValueError("exploration must be finite and non-negative")
    if not support.concrete_states:
        raise ValueError("local resolver requires compatible concrete states")

    root_key = support.information_state_key
    for state in support.concrete_states:
        if information_state_key(state) != root_key:
            raise AssertionError("compatible-state support leaked across information sets")
        if state.actor != support.actor or state.round_index != support.round_index:
            raise AssertionError("compatible-state support changed actor or round")
        action_keys = tuple(key for key, _action in legal_action_pairs(state))
        if action_keys != support.action_keys:
            raise AssertionError("compatible-state support changed root legal actions")

    rng = random.Random(int(seed))
    bandit = _LocalBandit(support.action_keys)

    def rollout(state: HUState) -> float:
        while not state.terminal():
            info_key = information_state_key(state)
            pairs = tuple(legal_action_pairs(state))
            action_keys = tuple(key for key, _action in pairs)
            profile = frozen_p0_profile if state.actor == 0 else frozen_p1_profile
            distribution = _normalize_distribution(profile, info_key, action_keys)
            selected = _sample_action(distribution, action_keys, rng)
            state = child_state(state, dict(pairs)[selected])
        return float(terminal_utility(state, 0))

    maximize = support.actor == 0
    for _ in range(iterations):
        # Critical firewall: root action is chosen before a hidden compatible
        # concrete state is sampled.
        action_key = bandit.select(maximize=maximize, exploration=exploration)
        concrete = support.concrete_states[rng.randrange(len(support.concrete_states))]
        root_action = dict(legal_action_pairs(concrete))[action_key]
        value = rollout(child_state(concrete, root_action))
        bandit.observe(action_key, value)

    distribution = tuple(
        (key, bandit.visits[key] / bandit.total_visits)
        for key in support.action_keys
    )
    return LocalResolveResult(
        information_state_key=root_key,
        actor=support.actor,
        iterations=iterations,
        compatible_states=len(support.concrete_states),
        action_visits=tuple((key, bandit.visits[key]) for key in support.action_keys),
        action_mean_u0=tuple(
            (key, bandit.sums[key] / bandit.visits[key]) for key in support.action_keys
        ),
        distribution=distribution,
    )


def complete_profile_with_counterfactual_resolve(
    base_profile: ReadOnlyProfile,
    support_rows: Sequence[ReachableInfoSetSupport],
    *,
    iterations_per_infoset: int,
    seed: int,
    exploration: float = 1.0,
) -> CompletionReport:
    """Complete a frozen base profile on every reachable information state.

    Every missing state is resolved against the same immutable base profile.
    Newly resolved decisions never affect another local resolver in this pass.
    """
    if not support_rows:
        raise ValueError("profile completion requires reachable information states")
    max_actions = max(len(row.action_keys) for row in support_rows)
    if iterations_per_infoset < max_actions:
        raise ValueError(
            f"iterations_per_infoset={iterations_per_infoset} is below max legal action count={max_actions}"
        )

    reachable_keys = {row.information_state_key for row in support_rows}
    frozen_base: BehaviorProfile = {
        key: {action: float(probability) for action, probability in distribution.items()}
        for key, distribution in base_profile.items()
    }
    completed: BehaviorProfile = {
        key: dict(distribution)
        for key, distribution in frozen_base.items()
        if key in reachable_keys
    }
    base_count = len(completed)

    # Both arguments deliberately point at the same immutable mixed profile;
    # only the acting player's information-state keys are consulted downstream.
    for row in support_rows:
        if row.information_state_key in completed:
            # Validate the supplied policy now so that a malformed base profile
            # cannot silently become a completed profile.
            completed[row.information_state_key] = _normalize_distribution(
                frozen_base, row.information_state_key, row.action_keys
            )
            continue
        resolved = resolve_missing_infoset(
            row,
            frozen_p0_profile=frozen_base,
            frozen_p1_profile=frozen_base,
            iterations=iterations_per_infoset,
            seed=_derived_seed(seed, row.information_state_key),
            exploration=exploration,
        )
        completed[row.information_state_key] = dict(resolved.distribution)

    p0_count = sum(1 for row in support_rows if row.actor == 0)
    p1_count = sum(1 for row in support_rows if row.actor == 1)
    return CompletionReport(
        authority=AUTHORITY,
        reachable_information_states=len(support_rows),
        base_information_states_on_support=base_count,
        resolved_information_states=len(support_rows) - base_count,
        completed_information_states=len(completed),
        p0_information_states=p0_count,
        p1_information_states=p1_count,
        iterations_per_resolved_infoset=iterations_per_infoset,
        seed=int(seed),
        exploration=float(exploration),
        profile=completed,
    )


def exact_profile_value_strict(
    base_state: HUState,
    worlds: Iterable[TwoStreetWorld],
    *,
    support_rows: Sequence[ReachableInfoSetSupport],
    p0_profile: ReadOnlyProfile,
    p1_profile: ReadOnlyProfile,
) -> ExactProfileEvaluation:
    """Evaluate fixed profiles only if every reachable acting infoset is explicit."""
    missing_p0 = [
        row.information_state_key
        for row in support_rows
        if row.actor == 0 and row.information_state_key not in p0_profile
    ]
    missing_p1 = [
        row.information_state_key
        for row in support_rows
        if row.actor == 1 and row.information_state_key not in p1_profile
    ]
    if missing_p0 or missing_p1:
        raise ValueError(
            "strict profile evaluation refuses unseen infosets: "
            f"missing_p0={len(missing_p0)} missing_p1={len(missing_p1)}"
        )
    return exact_profile_value(
        base_state,
        worlds,
        p0_profile=p0_profile,
        p1_profile=p1_profile,
    )


__all__ = [
    "AUTHORITY",
    "SCHEMA",
    "ReachableInfoSetSupport",
    "LocalResolveResult",
    "CompletionReport",
    "build_reachable_infoset_support",
    "resolve_missing_infoset",
    "complete_profile_with_counterfactual_resolve",
    "exact_profile_value_strict",
]
