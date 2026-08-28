from __future__ import annotations

"""One-pass reach-weighted local completion for 05F Search snapshots.

The hidden-state prior at each missing information set is the exact acting-player
counterfactual reach induced by an immutable, complete reference profile.
Original observed Search decisions are preserved and newly resolved decisions do
not bootstrap one another.

Authority:
  HIDDEN_DISCARD_REACH_WEIGHTED_COMPLETION_SHADOW_ONLY
"""

from dataclasses import dataclass
import hashlib
import math
import random
from typing import Mapping, Sequence

from external_hidden_discard_overlap import OverlapWorld, validate_worlds, with_overlap_world
from external_hidden_discard_overlap_strategic import BehaviorProfile, ReachableSupport
from strategic_cfr import HUState, child_state, information_state_key, legal_action_pairs, terminal_utility

AUTHORITY = "HIDDEN_DISCARD_REACH_WEIGHTED_COMPLETION_SHADOW_ONLY"
SCHEMA = "openofc-external-hidden-discard-reach-completion-v1"
ReadOnlyProfile = Mapping[str, Mapping[str, float]]


@dataclass(frozen=True)
class CounterfactualPrior:
    information_state_key: str
    round_index: int
    actor: int
    compatible_states: int
    positive_states: int
    zero_counterfactual_mass: bool
    uniform_tv: float | None
    state_probabilities: tuple[tuple[str, float], ...]


@dataclass(frozen=True)
class ReachWeightedCompletionReport:
    authority: str
    reachable_information_states: int
    original_information_states: int
    resolved_information_states: int
    positive_counterfactual_resolutions: int
    zero_counterfactual_fallback_resolutions: int
    iterations_per_resolved_infoset: int
    seed: int
    exploration: float
    profile: BehaviorProfile


def _normalize_explicit(profile: ReadOnlyProfile, key: str, action_keys: Sequence[str]) -> dict[str, float]:
    supplied = profile.get(key)
    if supplied is None:
        raise ValueError(f"complete reference profile missing infoset: {key}")
    legal = tuple(action_keys)
    illegal = set(supplied) - set(legal)
    if illegal:
        raise ValueError(f"profile contains illegal actions: {sorted(illegal)}")
    weights = {}
    for action_key in legal:
        value = float(supplied.get(action_key, 0.0))
        if value < 0.0 or not math.isfinite(value):
            raise ValueError("profile probabilities must be finite and non-negative")
        weights[action_key] = value
    mass = sum(weights.values())
    if mass <= 0.0:
        raise ValueError("reference profile has zero legal probability mass")
    return {key: value / mass for key, value in weights.items()}


def _tv_uniform(probabilities: Sequence[float]) -> float:
    if not probabilities:
        raise ValueError("cannot compare empty prior")
    u = 1.0 / len(probabilities)
    return 0.5 * sum(abs(float(value) - u) for value in probabilities)


def build_counterfactual_priors(
    base_state: HUState,
    worlds: Sequence[OverlapWorld],
    *,
    support_rows: Sequence[ReachableSupport],
    reference_profile: ReadOnlyProfile,
) -> tuple[CounterfactualPrior, ...]:
    """Enumerate exact acting-player counterfactual state weights.

    The reference profile must be explicit at every reachable information set.
    All action branches are traversed even when their own-strategy probability
    is zero, because a later information set of that same player can retain
    positive counterfactual reach.
    """
    support = validate_worlds(worlds)
    if not support_rows:
        raise ValueError("counterfactual priors require support rows")
    row_by_key = {row.information_state_key: row for row in support_rows}
    if len(row_by_key) != len(support_rows):
        raise ValueError("support rows contain duplicate information-state keys")
    missing = set(row_by_key) - set(reference_profile)
    if missing:
        raise ValueError(f"reference profile incomplete: missing={len(missing)}")

    # key -> concrete state repr -> counterfactual reach mass
    accum: dict[str, dict[str, float]] = {key: {} for key in row_by_key}
    chance = 1.0 / len(support)

    def walk(state: HUState, reach0: float, reach1: float) -> None:
        if state.terminal():
            return
        key = information_state_key(state)
        row = row_by_key.get(key)
        if row is None:
            raise AssertionError("reference traversal reached infoset outside exact support")
        fingerprint = repr(state)
        cf = chance * (reach1 if state.actor == 0 else reach0)
        accum[key][fingerprint] = accum[key].get(fingerprint, 0.0) + cf

        pairs = tuple(legal_action_pairs(state))
        action_keys = tuple(action_key for action_key, _action in pairs)
        if action_keys != row.action_keys:
            raise AssertionError("reference traversal action set disagrees with support row")
        distribution = _normalize_explicit(reference_profile, key, action_keys)
        by_key = dict(pairs)
        for action_key in action_keys:
            probability = distribution[action_key]
            if state.actor == 0:
                walk(child_state(state, by_key[action_key]), reach0 * probability, reach1)
            else:
                walk(child_state(state, by_key[action_key]), reach0, reach1 * probability)

    for world in support:
        walk(with_overlap_world(base_state, world), 1.0, 1.0)

    priors = []
    for row in support_rows:
        fingerprints = tuple(repr(state) for state in row.concrete_states)
        if len(set(fingerprints)) != len(fingerprints):
            raise AssertionError("support row contains duplicate concrete states")
        raw = [float(accum[row.information_state_key].get(fingerprint, 0.0)) for fingerprint in fingerprints]
        mass = sum(raw)
        if mass > 0.0:
            probabilities = tuple(value / mass for value in raw)
            zero = False
            uniform_tv = _tv_uniform(probabilities)
        else:
            probabilities = tuple(1.0 / len(fingerprints) for _ in fingerprints)
            zero = True
            uniform_tv = None
        priors.append(
            CounterfactualPrior(
                information_state_key=row.information_state_key,
                round_index=row.round_index,
                actor=row.actor,
                compatible_states=len(fingerprints),
                positive_states=sum(1 for value in raw if value > 0.0),
                zero_counterfactual_mass=zero,
                uniform_tv=uniform_tv,
                state_probabilities=tuple(zip(fingerprints, probabilities)),
            )
        )
    return tuple(priors)


class _Bandit:
    def __init__(self, action_keys: Sequence[str]) -> None:
        self.action_keys = tuple(action_keys)
        if not self.action_keys:
            raise ValueError("local resolver requires legal actions")
        self.visits = {key: 0 for key in self.action_keys}
        self.sums = {key: 0.0 for key in self.action_keys}
        self.total = 0

    def select(self, *, maximize: bool, exploration: float) -> str:
        unseen = [key for key in self.action_keys if self.visits[key] == 0]
        if unseen:
            return unseen[0]
        log_total = math.log(self.total + 1.0)
        def mean(key: str) -> float:
            return self.sums[key] / self.visits[key]
        if maximize:
            return max(
                self.action_keys,
                key=lambda key: (
                    mean(key) + exploration * math.sqrt(log_total / self.visits[key]),
                    -self.action_keys.index(key),
                ),
            )
        return min(
            self.action_keys,
            key=lambda key: (
                mean(key) - exploration * math.sqrt(log_total / self.visits[key]),
                self.action_keys.index(key),
            ),
        )

    def observe(self, key: str, value: float) -> None:
        self.visits[key] += 1
        self.sums[key] += float(value)
        self.total += 1


def _derived_seed(base_seed: int, info_key: str) -> int:
    digest = hashlib.sha256(f"{int(base_seed)}|{info_key}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def _sample_index(probabilities: Sequence[float], rng: random.Random) -> int:
    x = rng.random()
    cumulative = 0.0
    for index, probability in enumerate(probabilities):
        cumulative += float(probability)
        if x <= cumulative or index == len(probabilities) - 1:
            return index
    raise AssertionError("prior sampling fell through")


def _sample_action(distribution: Mapping[str, float], action_keys: Sequence[str], rng: random.Random) -> str:
    x = rng.random()
    cumulative = 0.0
    for index, key in enumerate(action_keys):
        cumulative += float(distribution[key])
        if x <= cumulative or index == len(action_keys) - 1:
            return key
    raise AssertionError("action sampling fell through")


def complete_with_counterfactual_priors(
    original_profile: ReadOnlyProfile,
    support_rows: Sequence[ReachableSupport],
    *,
    reference_profile: ReadOnlyProfile,
    priors: Sequence[CounterfactualPrior],
    iterations_per_resolved_infoset: int,
    seed: int,
    exploration: float = 1.0,
) -> ReachWeightedCompletionReport:
    """Complete only states absent from the original snapshot.

    Hidden-state priors and downstream rollout policy are frozen from the complete
    reference profile. Newly generated decisions are never consulted by another
    resolver during this pass.
    """
    if not support_rows:
        raise ValueError("completion requires reachable support")
    if exploration < 0.0 or not math.isfinite(exploration):
        raise ValueError("exploration must be finite and non-negative")
    max_actions = max(len(row.action_keys) for row in support_rows)
    if iterations_per_resolved_infoset < max_actions:
        raise ValueError("completion budget must visit every local action")
    row_by_key = {row.information_state_key: row for row in support_rows}
    prior_by_key = {prior.information_state_key: prior for prior in priors}
    if set(prior_by_key) != set(row_by_key):
        raise ValueError("counterfactual priors do not cover exact support")
    if set(row_by_key) - set(reference_profile):
        raise ValueError("reference profile must be complete")

    frozen_original: BehaviorProfile = {
        key: {action: float(probability) for action, probability in dist.items()}
        for key, dist in original_profile.items()
        if key in row_by_key
    }
    completed: BehaviorProfile = {}
    for key, dist in frozen_original.items():
        row = row_by_key[key]
        # Preserve policy semantics while normalizing and validating it.
        completed[key] = _normalize_explicit(frozen_original, key, row.action_keys)

    positive_cf = 0
    zero_cf = 0
    for row in support_rows:
        key = row.information_state_key
        if key in completed:
            continue
        prior = prior_by_key[key]
        if prior.zero_counterfactual_mass:
            zero_cf += 1
        else:
            positive_cf += 1
        state_by_fingerprint = {repr(state): state for state in row.concrete_states}
        fingerprints = tuple(fingerprint for fingerprint, _probability in prior.state_probabilities)
        probabilities = tuple(probability for _fingerprint, probability in prior.state_probabilities)
        if set(fingerprints) != set(state_by_fingerprint):
            raise AssertionError("prior concrete support disagrees with reachable support")

        rng = random.Random(_derived_seed(seed, key))
        bandit = _Bandit(row.action_keys)
        for _ in range(iterations_per_resolved_infoset):
            # Firewall: choose the information-set action before drawing a hidden
            # concrete state from the counterfactual posterior.
            root_action_key = bandit.select(maximize=row.actor == 0, exploration=exploration)
            index = _sample_index(probabilities, rng)
            state = state_by_fingerprint[fingerprints[index]]
            root_action = dict(legal_action_pairs(state))[root_action_key]
            state = child_state(state, root_action)
            while not state.terminal():
                downstream_key = information_state_key(state)
                pairs = tuple(legal_action_pairs(state))
                action_keys = tuple(action_key for action_key, _action in pairs)
                distribution = _normalize_explicit(reference_profile, downstream_key, action_keys)
                selected = _sample_action(distribution, action_keys, rng)
                state = child_state(state, dict(pairs)[selected])
            bandit.observe(root_action_key, float(terminal_utility(state, 0)))
        completed[key] = {
            action_key: bandit.visits[action_key] / bandit.total
            for action_key in row.action_keys
        }

    if set(completed) != set(row_by_key):
        raise AssertionError("reach-weighted completion did not cover all reachable infosets")
    return ReachWeightedCompletionReport(
        authority=AUTHORITY,
        reachable_information_states=len(support_rows),
        original_information_states=len(frozen_original),
        resolved_information_states=len(support_rows) - len(frozen_original),
        positive_counterfactual_resolutions=positive_cf,
        zero_counterfactual_fallback_resolutions=zero_cf,
        iterations_per_resolved_infoset=int(iterations_per_resolved_infoset),
        seed=int(seed),
        exploration=float(exploration),
        profile=completed,
    )


__all__ = [
    "AUTHORITY", "SCHEMA", "CounterfactualPrior", "ReachWeightedCompletionReport",
    "build_counterfactual_priors", "complete_with_counterfactual_priors",
]
