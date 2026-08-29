from __future__ import annotations

"""Counterfactual-weighted local-backward completion core for conditional 05G-Q4A.

This module deliberately mirrors `external_05g_uniform_backward_completion`
except that each infoset may receive externally frozen non-negative weights over
its exact `ReachableSupport.concrete_states`.  It is a one-shot completion
component, not an iterative solver.
"""

from dataclasses import dataclass
import hashlib
import math
from typing import Mapping, Sequence

from external_hidden_discard_overlap_strategic import ReachableSupport
from strategic_cfr import HUState, child_state, information_state_key, legal_action_pairs, terminal_utility

AUTHORITY = "BROAD_HIDDEN_INFORMATION_REDUCED_GAME_SHADOW_ONLY"
SCHEMA = "openofc-external-05g-counterfactual-weighted-local-backward-completion-v1"
SOURCE_LABEL = "COMPLETION_COUNTERFACTUAL_WEIGHTED_LOCAL_BACKWARD_V1"
LAYER_ORDER = ((4, 1), (4, 0), (3, 1), (3, 0))
WEIGHT_TOLERANCE = 1e-15
TIE_TOLERANCE = 1e-12

FrozenStateWeights = Mapping[str, Mapping[str, float]]


@dataclass(frozen=True)
class WeightedCompletionBuild:
    schema: str
    authority: str
    source_label: str
    information_states: int
    positive_weight_information_states: int
    zero_weight_fallback_information_states: int
    terminal_evaluations: int
    rollout_cache_entries: int
    layer_counts: tuple[tuple[str, int], ...]
    policy_sha256: str
    selected_actions: tuple[tuple[str, str], ...]

    def choice_map(self) -> dict[str, str]:
        return dict(self.selected_actions)


def completion_policy_sha256(choices: Mapping[str, str]) -> str:
    digest = hashlib.sha256()
    for info_key in sorted(choices):
        digest.update(hashlib.sha256(info_key.encode("utf-8")).digest())
        digest.update(b"\0")
        digest.update(choices[info_key].encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _choose_best(values: Mapping[str, float], *, maximize: bool) -> str:
    if not values:
        raise ValueError("cannot choose from empty action values")
    ordered = sorted(values)
    best_key = ordered[0]
    best_value = float(values[best_key])
    for key in ordered[1:]:
        value = float(values[key])
        better = value > best_value if maximize else value < best_value
        if better and not math.isclose(value, best_value, rel_tol=0.0, abs_tol=TIE_TOLERANCE):
            best_key = key
            best_value = value
        elif math.isclose(value, best_value, rel_tol=0.0, abs_tol=TIE_TOLERANCE) and key < best_key:
            best_key = key
            best_value = value
    return best_key


def build_counterfactual_weighted_local_backward_completion(
    support_rows: Sequence[ReachableSupport],
    *,
    frozen_state_weights: FrozenStateWeights,
    zero_weight_fallback_choices: Mapping[str, str],
) -> WeightedCompletionBuild:
    """Build a pure backward completion from a frozen state-weight map.

    Positive raw weights are normalized independently inside each infoset.  If
    total frozen weight is zero, the exact supplied fallback action is retained.
    Newly selected actions affect only downstream local-completion rollouts; the
    frozen weights are never recomputed, preserving Q4A's one-shot causal A/B.
    """

    if not support_rows:
        raise ValueError("weighted completion requires exhaustive support rows")
    by_key = {row.information_state_key: row for row in support_rows}
    if len(by_key) != len(support_rows):
        raise AssertionError("support contains duplicate information-state keys")
    if set(zero_weight_fallback_choices) != set(by_key):
        raise ValueError("zero-weight fallback must cover exhaustive support exactly")
    observed_layers = {(row.round_index, row.actor) for row in support_rows}
    if observed_layers != set(LAYER_ORDER):
        raise ValueError(f"unsupported completion layers: {sorted(observed_layers)}")

    # Validate that supplied weight maps never refer to a non-support infoset or
    # concrete-state fingerprint. Missing weights for an expected state are zero.
    extra_infosets = set(frozen_state_weights) - set(by_key)
    if extra_infosets:
        raise ValueError("frozen weights contain non-support infosets")
    fingerprints_by_key = {
        row.information_state_key: {repr(state) for state in row.concrete_states}
        for row in support_rows
    }
    for info_key, bucket in frozen_state_weights.items():
        extra = set(bucket) - fingerprints_by_key[info_key]
        if extra:
            raise ValueError("frozen weights contain non-support concrete state")
        for value in bucket.values():
            weight = float(value)
            if not math.isfinite(weight) or weight < 0.0:
                raise ValueError("frozen state weights must be finite and non-negative")

    choices: dict[str, str] = {}
    rollout_cache: dict[str, float] = {}
    terminal_evaluations = 0
    positive_weight_infosets = 0
    zero_weight_fallback_infosets = 0
    layer_counts: list[tuple[str, int]] = []

    def rollout(state: HUState) -> float:
        nonlocal terminal_evaluations
        fingerprint = repr(state)
        cached = rollout_cache.get(fingerprint)
        if cached is not None:
            return cached
        current = state
        while not current.terminal():
            key = information_state_key(current)
            selected = choices.get(key)
            if selected is None:
                raise AssertionError(
                    "weighted backward completion encountered unresolved later infoset "
                    f"at R{current.round_index} P{current.actor}"
                )
            pairs = dict(legal_action_pairs(current))
            if selected not in pairs:
                raise AssertionError("stored weighted-completion action is illegal")
            current = child_state(current, pairs[selected])
        terminal_evaluations += 1
        value = float(terminal_utility(current, 0))
        rollout_cache[fingerprint] = value
        return value

    for round_index, actor in LAYER_ORDER:
        rows = sorted(
            (row for row in support_rows if (row.round_index, row.actor) == (round_index, actor)),
            key=lambda row: row.information_state_key,
        )
        layer_counts.append((f"R{round_index}_P{actor}", len(rows)))
        for row in rows:
            info_key = row.information_state_key
            if not row.concrete_states:
                raise AssertionError("reachable infoset must contain compatible concrete states")
            raw_bucket = frozen_state_weights.get(info_key, {})
            state_weight_pairs = [
                (state, float(raw_bucket.get(repr(state), 0.0)))
                for state in row.concrete_states
            ]
            total_weight = sum(weight for _state, weight in state_weight_pairs)

            if total_weight <= WEIGHT_TOLERANCE:
                selected = zero_weight_fallback_choices[info_key]
                if selected not in row.action_keys:
                    raise AssertionError("zero-weight fallback selected illegal action")
                choices[info_key] = selected
                zero_weight_fallback_infosets += 1
                continue

            positive_weight_infosets += 1
            action_values: dict[str, float] = {}
            for action_key in row.action_keys:
                weighted_total = 0.0
                for state, raw_weight in state_weight_pairs:
                    if raw_weight <= 0.0:
                        continue
                    pairs = dict(legal_action_pairs(state))
                    action = pairs.get(action_key)
                    if action is None:
                        raise AssertionError("infoset action set differs across compatible concrete states")
                    child = child_state(state, action)
                    if child.terminal():
                        terminal_evaluations += 1
                        value = float(terminal_utility(child, 0))
                    else:
                        value = rollout(child)
                    weighted_total += (raw_weight / total_weight) * value
                action_values[action_key] = weighted_total
            choices[info_key] = _choose_best(action_values, maximize=actor == 0)

    if set(choices) != set(by_key):
        raise AssertionError("weighted completion did not cover exhaustive support")
    if positive_weight_infosets + zero_weight_fallback_infosets != len(support_rows):
        raise AssertionError("weighted completion source accounting mismatch")
    for info_key, action_key in choices.items():
        if action_key not in by_key[info_key].action_keys:
            raise AssertionError("weighted completion contains illegal action")

    return WeightedCompletionBuild(
        schema=SCHEMA,
        authority=AUTHORITY,
        source_label=SOURCE_LABEL,
        information_states=len(choices),
        positive_weight_information_states=positive_weight_infosets,
        zero_weight_fallback_information_states=zero_weight_fallback_infosets,
        terminal_evaluations=terminal_evaluations,
        rollout_cache_entries=len(rollout_cache),
        layer_counts=tuple(layer_counts),
        policy_sha256=completion_policy_sha256(choices),
        selected_actions=tuple((key, choices[key]) for key in sorted(choices)),
    )


__all__ = [
    "AUTHORITY",
    "SCHEMA",
    "SOURCE_LABEL",
    "LAYER_ORDER",
    "WEIGHT_TOLERANCE",
    "TIE_TOLERANCE",
    "WeightedCompletionBuild",
    "completion_policy_sha256",
    "build_counterfactual_weighted_local_backward_completion",
]
