from __future__ import annotations

"""Learner-independent pure completion baseline for 05G.

The completion is built backward over the finite R3->R4 reduced game. At each
information set it chooses one action before the hidden concrete state is drawn,
using a uniform average over compatible concrete states and the already-frozen
completion choices at later layers.

This is intentionally a local-uniform completion baseline, not a claim of a
Bayesian posterior, equilibrium value, or production strategy.
"""

from dataclasses import dataclass
import hashlib
import math
from typing import Mapping, Sequence

from external_hidden_discard_overlap_strategic import ReachableSupport
from strategic_cfr import HUState, child_state, information_state_key, legal_action_pairs, terminal_utility

AUTHORITY = "BROAD_HIDDEN_INFORMATION_REDUCED_GAME_SHADOW_ONLY"
SCHEMA = "openofc-external-05g-uniform-local-backward-completion-v1"
SOURCE_LABEL = "COMPLETION_UNIFORM_LOCAL_BACKWARD_V1"
LAYER_ORDER = ((4, 1), (4, 0), (3, 1), (3, 0))


@dataclass(frozen=True)
class CompletionBuild:
    schema: str
    authority: str
    source_label: str
    information_states: int
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
        if better and not math.isclose(value, best_value, rel_tol=0.0, abs_tol=1e-12):
            best_key = key
            best_value = value
        elif math.isclose(value, best_value, rel_tol=0.0, abs_tol=1e-12) and key < best_key:
            best_key = key
            best_value = value
    return best_key


def build_uniform_local_backward_completion(
    support_rows: Sequence[ReachableSupport],
) -> CompletionBuild:
    if not support_rows:
        raise ValueError("completion requires exhaustive support rows")

    by_key = {row.information_state_key: row for row in support_rows}
    if len(by_key) != len(support_rows):
        raise AssertionError("support contains duplicate information-state keys")

    observed_layers = {(row.round_index, row.actor) for row in support_rows}
    expected_layers = set(LAYER_ORDER)
    if observed_layers != expected_layers:
        raise ValueError(f"unsupported completion layers: {sorted(observed_layers)}")

    choices: dict[str, str] = {}
    rollout_cache: dict[str, float] = {}
    terminal_evaluations = 0
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
                    "backward completion encountered an unresolved later infoset "
                    f"at R{current.round_index} P{current.actor}"
                )
            pairs = dict(legal_action_pairs(current))
            if selected not in pairs:
                raise AssertionError("stored completion action is illegal in a compatible concrete state")
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
            if not row.concrete_states:
                raise AssertionError("reachable infoset must contain compatible concrete states")
            action_values: dict[str, float] = {}
            for action_key in row.action_keys:
                total = 0.0
                for state in row.concrete_states:
                    pairs = dict(legal_action_pairs(state))
                    action = pairs.get(action_key)
                    if action is None:
                        raise AssertionError("infoset action set differs across compatible concrete states")
                    child = child_state(state, action)
                    if child.terminal():
                        terminal_evaluations += 1
                        total += float(terminal_utility(child, 0))
                    else:
                        total += rollout(child)
                action_values[action_key] = total / len(row.concrete_states)
            choices[row.information_state_key] = _choose_best(action_values, maximize=actor == 0)

    if set(choices) != set(by_key):
        raise AssertionError("completion did not cover the full exhaustive support")

    # Fail closed on legality one more time without evaluating payoff.
    for info_key, action_key in choices.items():
        row = by_key[info_key]
        if action_key not in row.action_keys:
            raise AssertionError("completion contains illegal selected action")

    return CompletionBuild(
        schema=SCHEMA,
        authority=AUTHORITY,
        source_label=SOURCE_LABEL,
        information_states=len(choices),
        terminal_evaluations=terminal_evaluations,
        rollout_cache_entries=len(rollout_cache),
        layer_counts=tuple(layer_counts),
        policy_sha256=completion_policy_sha256(choices),
        selected_actions=tuple((key, choices[key]) for key in sorted(choices)),
    )


def pure_behavior_profile(completion: CompletionBuild) -> dict[str, dict[str, float]]:
    return {
        info_key: {selected: 1.0}
        for info_key, selected in completion.selected_actions
    }


__all__ = [
    "AUTHORITY",
    "SCHEMA",
    "SOURCE_LABEL",
    "LAYER_ORDER",
    "CompletionBuild",
    "completion_policy_sha256",
    "build_uniform_local_backward_completion",
    "pure_behavior_profile",
]
