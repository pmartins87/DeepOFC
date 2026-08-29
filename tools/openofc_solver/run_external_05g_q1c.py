from __future__ import annotations

"""Run 05G-Q1C exact fixed-profile self/cross-play EV matrix.

This is a descriptive fixed-profile evaluation.  It deliberately computes no
best response, NashConv, exploitability, policy update, or strategic winner.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
from time import perf_counter
from typing import Mapping, Sequence

from external_05g_broad_support import (
    AUTHORITY,
    broad_worlds,
    public_pre_r3_state,
    support_sha256,
    validate_broad_physical_support,
)
from external_05g_uniform_backward_completion import build_uniform_local_backward_completion
from external_hidden_discard_overlap import run_overlap_infoset_uct, with_overlap_world
from external_hidden_discard_overlap_strategic import (
    OverlapExternalSamplingMCCFR,
    ReachableSupport,
    build_reachable_support,
    visit_profile_from_overlap_search,
)
from strategic_cfr import HUState, child_state, information_state_key, legal_action_pairs, terminal_utility
from run_external_05g_q0b import _support_maps, _validate_profile
from run_external_05g_q1a import (
    MCCFR_ITERATIONS,
    SEARCH_EXPLORATION,
    SEARCH_ITERATIONS,
    SEEDS,
    _profile_sha256,
)
from run_external_05g_q1b import _assemble_completed, _materialize_completion_profile

EXPERIMENT_ID = "EXT-05G-Q1C-EXACT-FIXED-PROFILE-EV"
PROFILE_NAMES = ("S", "M", "H")

BehaviorProfile = Mapping[str, Mapping[str, float]]


def _exact_asymmetric_value(
    base_state: HUState,
    worlds,
    *,
    p0_profile: BehaviorProfile,
    p1_profile: BehaviorProfile,
) -> dict:
    cache: dict[HUState, float] = {}
    terminal_states = 0
    missing_lookups = 0
    action_probability_mass_checks = 0

    def walk(state: HUState) -> float:
        nonlocal terminal_states, missing_lookups, action_probability_mass_checks
        cached = cache.get(state)
        if cached is not None:
            return cached
        if state.terminal():
            terminal_states += 1
            value = float(terminal_utility(state, 0))
            cache[state] = value
            return value

        profile = p0_profile if state.actor == 0 else p1_profile
        info_key = information_state_key(state)
        distribution = profile.get(info_key)
        if distribution is None:
            missing_lookups += 1
            raise ValueError("Q1C strict exact evaluation refuses missing infoset")
        pairs = tuple(legal_action_pairs(state))
        legal_keys = tuple(action_key for action_key, _action in pairs)
        if set(distribution) != set(legal_keys):
            raise ValueError("Q1C complete profile action set mismatch")
        probabilities = [float(distribution[action_key]) for action_key in legal_keys]
        if any((not math.isfinite(p)) or p < 0.0 for p in probabilities):
            raise ValueError("Q1C invalid profile probability")
        if not math.isclose(sum(probabilities), 1.0, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError("Q1C profile probability mass is not one")
        action_probability_mass_checks += 1
        by_key = dict(pairs)
        value = 0.0
        for action_key, probability in zip(legal_keys, probabilities):
            if probability <= 0.0:
                continue
            value += probability * walk(child_state(state, by_key[action_key]))
        cache[state] = value
        return value

    t0 = perf_counter()
    roots = [with_overlap_world(base_state, world) for world in worlds]
    values = [walk(root) for root in roots]
    runtime = perf_counter() - t0
    value = sum(values) / len(values)
    nonterminal_cached = sum(1 for state in cache if not state.terminal())
    terminal_cached = len(cache) - nonterminal_cached
    return {
        "expected_u0": value,
        "chance_roots": len(roots),
        "runtime_seconds": runtime,
        "memoized_states": len(cache),
        "memoized_nonterminal_states": nonterminal_cached,
        "memoized_terminal_states": terminal_cached,
        "terminal_state_evaluations": terminal_states,
        "probability_mass_checks": action_probability_mass_checks,
        "missing_profile_lookups": missing_lookups,
        "finite": math.isfinite(value),
    }


def _materialize_seed_profiles(
    *,
    seed: int,
    base_state,
    worlds,
    support_rows: Sequence[ReachableSupport],
    completion_profile: BehaviorProfile,
) -> dict:
    t0 = perf_counter()
    search_result = run_overlap_infoset_uct(
        base_state,
        worlds,
        iterations=SEARCH_ITERATIONS,
        seed=seed,
        exploration=SEARCH_EXPLORATION,
    )
    search = visit_profile_from_overlap_search(search_result)
    search_seconds = perf_counter() - t0

    t1 = perf_counter()
    mccfr_solver = OverlapExternalSamplingMCCFR(base_state, worlds, seed=seed)
    mccfr_solver.run(MCCFR_ITERATIONS)
    mccfr = mccfr_solver.current_profile()
    mccfr_seconds = perf_counter() - t1

    profiles: dict[str, dict[str, dict[str, float]]] = {}
    source_maps: dict[str, dict[str, str]] = {}
    for name in PROFILE_NAMES:
        profile, source_map = _assemble_completed(
            mode=name,
            support_rows=support_rows,
            search=search,
            mccfr=mccfr,
            completion=completion_profile,
        )
        profiles[name] = profile
        source_maps[name] = source_map
    return {
        "profiles": profiles,
        "source_maps": source_maps,
        "native_runtime_seconds": {"search": search_seconds, "mccfr": mccfr_seconds},
        "native_counts": {"search": len(search), "mccfr": len(mccfr)},
        "native_sha256": {"search": _profile_sha256(search), "mccfr": _profile_sha256(mccfr)},
    }


def run() -> dict:
    worlds = broad_worlds()
    base_state = public_pre_r3_state()
    validate_broad_physical_support(base_state, worlds)
    support_rows = build_reachable_support(base_state, worlds)
    support_by_key, nonroot_keys, ambiguous_nonroot_keys, root_keys = _support_maps(support_rows)
    if len(worlds) != 36 or len(root_keys) != 3:
        raise RuntimeError("05G frozen support geometry changed")

    t0 = perf_counter()
    completion = build_uniform_local_backward_completion(support_rows)
    completion_seconds = perf_counter() - t0
    completion_profile = _materialize_completion_profile(support_rows, completion.choice_map())

    seed_results = []
    world_ids = tuple(world.world_id for world in worlds)
    for seed in SEEDS:
        materialized = _materialize_seed_profiles(
            seed=seed,
            base_state=base_state,
            worlds=worlds,
            support_rows=support_rows,
            completion_profile=completion_profile,
        )
        profiles = materialized["profiles"]
        profile_hashes = {name: _profile_sha256(profiles[name]) for name in PROFILE_NAMES}
        profile_validation = {
            name: _validate_profile(profiles[name], support_by_key, world_ids)
            for name in PROFILE_NAMES
        }
        validation_pass = all(
            validation[field] == 0
            for validation in profile_validation.values()
            for field in (
                "illegal_key_count",
                "action_set_mismatch_count",
                "invalid_distribution_count",
                "hidden_world_token_leakage_count",
            )
        ) and all(set(profiles[name]) == set(support_by_key) for name in PROFILE_NAMES)

        matrix = []
        for p0_name in PROFILE_NAMES:
            for p1_name in PROFILE_NAMES:
                evaluation = _exact_asymmetric_value(
                    base_state,
                    worlds,
                    p0_profile=profiles[p0_name],
                    p1_profile=profiles[p1_name],
                )
                matrix.append({
                    "p0_profile": p0_name,
                    "p1_profile": p1_name,
                    **evaluation,
                })

        matrix_pass = len(matrix) == 9 and all(
            row["finite"]
            and row["chance_roots"] == 36
            and row["missing_profile_lookups"] == 0
            for row in matrix
        )
        seed_results.append({
            "seed": seed,
            "profile_sha256": profile_hashes,
            "profile_validation": profile_validation,
            "native_profile_sha256": materialized["native_sha256"],
            "native_information_states": materialized["native_counts"],
            "native_runtime_seconds": materialized["native_runtime_seconds"],
            "matrix": matrix,
            "seed_pass": validation_pass and matrix_pass,
        })

    # Descriptive between-seed stability only; never a promotion criterion.
    stability = []
    by_seed = {
        row["seed"]: {(cell["p0_profile"], cell["p1_profile"]): cell["expected_u0"] for cell in row["matrix"]}
        for row in seed_results
    }
    if len(SEEDS) == 2:
        a, b = SEEDS
        for pair in ((x, y) for x in PROFILE_NAMES for y in PROFILE_NAMES):
            stability.append({
                "p0_profile": pair[0],
                "p1_profile": pair[1],
                "seed_a": a,
                "seed_b": b,
                "absolute_ev_difference": abs(by_seed[a][pair] - by_seed[b][pair]),
                "diagnostic_only": True,
            })

    quality = {
        "support_36_worlds": len(worlds) == 36,
        "completion_policy_complete": completion.information_states == len(support_rows),
        "both_seeds_pass": len(seed_results) == 2 and all(row["seed_pass"] for row in seed_results),
        "exact_18_cells_total": sum(len(row["matrix"]) for row in seed_results) == 18,
        "all_cells_36_chance_roots_and_finite": all(
            cell["chance_roots"] == 36 and cell["finite"] and cell["missing_profile_lookups"] == 0
            for row in seed_results
            for cell in row["matrix"]
        ),
        "seeds_kept_separate": [row["seed"] for row in seed_results] == list(SEEDS),
        "no_sampling_in_evaluation": True,
        "no_best_response_used": True,
        "no_nashconv_or_exploitability_used": True,
        "no_strength_winner_claim": True,
    }
    passed = all(quality.values())

    source_paths = [
        "tools/openofc_solver/EXTERNAL_05G_BROAD_HIDDEN_INFORMATION_CONTRACT.md",
        "tools/openofc_solver/EXTERNAL_05G_Q1A_NATIVE_PROVENANCE_ROUTER_CONTRACT.md",
        "tools/openofc_solver/EXTERNAL_05G_Q1B_UNIFORM_BACKWARD_COMPLETION_CONTRACT.md",
        "tools/openofc_solver/EXTERNAL_05G_Q1C_FIXED_PROFILE_EV_CONTRACT.md",
        "tools/openofc_solver/external_05g_uniform_backward_completion.py",
        "tools/openofc_solver/run_external_05g_q1a.py",
        "tools/openofc_solver/run_external_05g_q1b.py",
        "tools/openofc_solver/run_external_05g_q1c.py",
    ]
    payload = {
        "schema": "openofc-external-component-ab-v1",
        "experiment_id": EXPERIMENT_ID,
        "authority": AUTHORITY,
        "component": "exact-fixed-profile-self-cross-play-descriptive-only",
        "config": {
            "seeds": list(SEEDS),
            "profiles": list(PROFILE_NAMES),
            "search_iterations": SEARCH_ITERATIONS,
            "search_exploration": SEARCH_EXPLORATION,
            "mccfr_iterations": MCCFR_ITERATIONS,
            "chance_worlds": len(worlds),
            "support_sha256": support_sha256(worlds),
            "completion_policy_sha256": completion.policy_sha256,
        },
        "exhaustive_support": {
            "reachable_information_states": len(support_rows),
            "nonroot_information_states": len(nonroot_keys),
            "ambiguous_nonroot_information_states": len(ambiguous_nonroot_keys),
        },
        "completion_build": {
            "runtime_seconds": completion_seconds,
            "terminal_evaluations": completion.terminal_evaluations,
            "policy_sha256": completion.policy_sha256,
        },
        "seed_results": seed_results,
        "between_seed_stability_diagnostic": stability,
        "quality": quality,
        "verdict": "PASS_EXACT_FIXED_PROFILE_EV" if passed else "BLOCK_EXACT_FIXED_PROFILE_EV",
        "promotion_recommendation": "CONTINUE_TO_Q2_EXACT_BILATERAL_BEST_RESPONSE" if passed else "FIX_Q1C_EVALUATION_MECHANICS_WITHOUT_CHANGING_FROZEN_PROFILES",
        "limitations": [
            "self-play and cross-play EV are descriptive and cannot rank equilibrium quality",
            "only Q2 exact bilateral best response/NashConv/exploitability may rank 05G profiles",
            "finite reduced 36-world game only",
            "no REAL route is certified",
        ],
        "files": [
            {"path": path, "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}
            for path in source_paths
        ],
        "real_routes_certified": 0,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    payload["sha256"] = hashlib.sha256(raw).hexdigest()
    if not passed:
        raise RuntimeError(f"05G-Q1C failed: {quality}")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/external_05g_q1c.json")
    args = parser.parse_args()
    payload = run()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "experiment_id": payload["experiment_id"],
        "verdict": payload["verdict"],
        "completion_policy_sha256": payload["completion_build"]["policy_sha256"],
        "seed_matrices": [
            {
                "seed": row["seed"],
                "cells": [
                    {
                        "p0": cell["p0_profile"],
                        "p1": cell["p1_profile"],
                        "u0": cell["expected_u0"],
                    }
                    for cell in row["matrix"]
                ],
            }
            for row in payload["seed_results"]
        ],
        "manifest_sha256": payload["sha256"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
