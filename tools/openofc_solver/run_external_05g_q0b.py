from __future__ import annotations

"""Run 05G-Q0B paired Search + MCCFR technical smoke.

This experiment intentionally measures execution, legal infoset fidelity and
learned coverage only. It does not complete missing policies, evaluate a policy
with uniform fallback, compute exact best responses, or declare a strategic
winner.
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
from external_hidden_discard_overlap import run_overlap_infoset_uct
from external_hidden_discard_overlap_strategic import (
    OverlapExternalSamplingMCCFR,
    ReachableSupport,
    build_reachable_support,
    visit_profile_from_overlap_search,
)

EXPERIMENT_ID = "EXT-05G-Q0B-SEARCH-MCCFR-TECHNICAL-SMOKE"
SEEDS = (20260829, 20260830)
BUDGET_PAIRS = (
    (2000, 64),
    (5000, 128),
)

BehaviorProfile = Mapping[str, Mapping[str, float]]


def _support_maps(rows: Sequence[ReachableSupport]) -> tuple[dict[str, ReachableSupport], set[str], set[str], tuple[str, ...]]:
    by_key = {row.information_state_key: row for row in rows}
    if len(by_key) != len(rows):
        raise AssertionError("reachable-support keys must be unique")
    nonroot = {
        row.information_state_key
        for row in rows
        if (row.round_index, row.actor) != (3, 0)
    }
    ambiguous_nonroot = {
        row.information_state_key
        for row in rows
        if (row.round_index, row.actor) != (3, 0) and len(row.concrete_states) > 1
    }
    roots = tuple(sorted(
        row.information_state_key
        for row in rows
        if (row.round_index, row.actor) == (3, 0)
    ))
    return by_key, nonroot, ambiguous_nonroot, roots


def _validate_profile(
    profile: BehaviorProfile,
    support_by_key: Mapping[str, ReachableSupport],
    world_ids: Sequence[str],
) -> dict:
    illegal_keys: list[str] = []
    action_set_mismatches: list[str] = []
    invalid_distributions: list[str] = []
    hidden_world_token_keys: list[str] = []

    for info_key, distribution in profile.items():
        row = support_by_key.get(info_key)
        if row is None:
            illegal_keys.append(info_key)
            continue
        if set(distribution) != set(row.action_keys):
            action_set_mismatches.append(info_key)
        values = [float(distribution.get(action_key, 0.0)) for action_key in row.action_keys]
        if (
            any((not math.isfinite(value)) or value < 0.0 for value in values)
            or not math.isclose(sum(values), 1.0, rel_tol=0.0, abs_tol=1e-9)
        ):
            invalid_distributions.append(info_key)
        if any(world_id in info_key for world_id in world_ids):
            hidden_world_token_keys.append(info_key)

    return {
        "materialized_information_states": len(profile),
        "illegal_key_count": len(illegal_keys),
        "action_set_mismatch_count": len(action_set_mismatches),
        "invalid_distribution_count": len(invalid_distributions),
        "hidden_world_token_leakage_count": len(hidden_world_token_keys),
        "illegal_key_examples": illegal_keys[:3],
        "action_set_mismatch_examples": action_set_mismatches[:3],
        "invalid_distribution_examples": invalid_distributions[:3],
        "hidden_world_token_examples": hidden_world_token_keys[:3],
    }


def _coverage(
    profile: BehaviorProfile,
    all_keys: set[str],
    nonroot_keys: set[str],
    ambiguous_nonroot_keys: set[str],
) -> dict:
    keys = set(profile)
    total_hit = len(keys & all_keys)
    nonroot_hit = len(keys & nonroot_keys)
    ambiguous_hit = len(keys & ambiguous_nonroot_keys)
    return {
        "total_hit": total_hit,
        "total_possible": len(all_keys),
        "total_ratio": total_hit / len(all_keys) if all_keys else 0.0,
        "nonroot_hit": nonroot_hit,
        "nonroot_possible": len(nonroot_keys),
        "nonroot_ratio": nonroot_hit / len(nonroot_keys) if nonroot_keys else 0.0,
        "ambiguous_nonroot_hit": ambiguous_hit,
        "ambiguous_nonroot_possible": len(ambiguous_nonroot_keys),
        "ambiguous_nonroot_ratio": ambiguous_hit / len(ambiguous_nonroot_keys) if ambiguous_nonroot_keys else 0.0,
    }


def _top_summary(distribution: Mapping[str, float]) -> dict:
    action, probability = max(
        distribution.items(),
        key=lambda item: (float(item[1]), item[0]),
    )
    return {
        "action": action,
        "probability": float(probability),
    }


def _root_diagnostics(
    search_profile: BehaviorProfile,
    mccfr_profile: BehaviorProfile,
    root_keys: Sequence[str],
) -> tuple[list[dict], bool, bool]:
    rows: list[dict] = []
    search_complete = all(key in search_profile for key in root_keys)
    mccfr_complete = all(key in mccfr_profile for key in root_keys)
    for index, info_key in enumerate(root_keys):
        s = search_profile.get(info_key)
        m = mccfr_profile.get(info_key)
        row = {
            "root_index": index,
            "information_state_sha256": hashlib.sha256(info_key.encode("utf-8")).hexdigest(),
            "search_present": s is not None,
            "mccfr_present": m is not None,
        }
        if s is not None:
            row["search_top"] = _top_summary(s)
        if m is not None:
            row["mccfr_top"] = _top_summary(m)
        if s is not None and m is not None:
            legal = sorted(set(s) | set(m))
            row["tv_distance"] = 0.5 * sum(abs(float(s.get(a, 0.0)) - float(m.get(a, 0.0))) for a in legal)
        rows.append(row)
    return rows, search_complete, mccfr_complete


def _trial(
    *,
    base_state,
    worlds,
    support_rows: Sequence[ReachableSupport],
    support_by_key: Mapping[str, ReachableSupport],
    nonroot_keys: set[str],
    ambiguous_nonroot_keys: set[str],
    root_keys: Sequence[str],
    search_iterations: int,
    mccfr_iterations: int,
    seed: int,
) -> dict:
    all_keys = set(support_by_key)
    world_ids = tuple(world.world_id for world in worlds)

    t0 = perf_counter()
    search_result = run_overlap_infoset_uct(
        base_state,
        worlds,
        iterations=search_iterations,
        seed=seed,
        exploration=1.0,
    )
    search_seconds = perf_counter() - t0
    search_profile = visit_profile_from_overlap_search(search_result)

    t1 = perf_counter()
    mccfr = OverlapExternalSamplingMCCFR(base_state, worlds, seed=seed)
    mccfr.run(mccfr_iterations)
    mccfr_seconds = perf_counter() - t1
    mccfr_profile = mccfr.current_profile()
    mccfr_snapshot = mccfr.snapshot()

    search_validation = _validate_profile(search_profile, support_by_key, world_ids)
    mccfr_validation = _validate_profile(mccfr_profile, support_by_key, world_ids)
    search_coverage = _coverage(search_profile, all_keys, nonroot_keys, ambiguous_nonroot_keys)
    mccfr_coverage = _coverage(mccfr_profile, all_keys, nonroot_keys, ambiguous_nonroot_keys)
    roots, search_roots_complete, mccfr_roots_complete = _root_diagnostics(
        search_profile,
        mccfr_profile,
        root_keys,
    )

    technical_pass = all((
        search_validation["illegal_key_count"] == 0,
        search_validation["action_set_mismatch_count"] == 0,
        search_validation["invalid_distribution_count"] == 0,
        search_validation["hidden_world_token_leakage_count"] == 0,
        mccfr_validation["illegal_key_count"] == 0,
        mccfr_validation["action_set_mismatch_count"] == 0,
        mccfr_validation["invalid_distribution_count"] == 0,
        mccfr_validation["hidden_world_token_leakage_count"] == 0,
        search_roots_complete,
        mccfr_roots_complete,
        search_coverage["nonroot_hit"] > 0,
        mccfr_coverage["nonroot_hit"] > 0,
    ))

    return {
        "seed": seed,
        "search_iterations": search_iterations,
        "mccfr_iterations": mccfr_iterations,
        "technical_pass": technical_pass,
        "search": {
            "runtime_seconds": search_seconds,
            "reported_information_states": search_result.information_states,
            "reported_ambiguous_information_states": search_result.ambiguous_information_states,
            "reported_ambiguous_nonroot_information_states": search_result.ambiguous_nonroot_information_states,
            "reported_max_compatible_worlds": search_result.max_compatible_worlds,
            "terminal_mean_u0_diagnostic_only": search_result.terminal_mean_u0,
            "validation": search_validation,
            "coverage": search_coverage,
        },
        "mccfr": {
            "runtime_seconds": mccfr_seconds,
            "reported_information_states": mccfr_snapshot.information_states,
            "terminal_evaluations": mccfr_snapshot.terminal_evaluations,
            "validation": mccfr_validation,
            "coverage": mccfr_coverage,
        },
        "root_diagnostics": roots,
        "search_all_roots_present": search_roots_complete,
        "mccfr_all_roots_present": mccfr_roots_complete,
    }


def run() -> dict:
    worlds = broad_worlds()
    base_state = public_pre_r3_state()
    validate_broad_physical_support(base_state, worlds)
    support_rows = build_reachable_support(base_state, worlds)
    support_by_key, nonroot_keys, ambiguous_nonroot_keys, root_keys = _support_maps(support_rows)

    if len(root_keys) != 3:
        raise RuntimeError(f"05G-Q0B expected exactly 3 P0-R3 root infosets, got {len(root_keys)}")

    trials = []
    for search_iterations, mccfr_iterations in BUDGET_PAIRS:
        for seed in SEEDS:
            trials.append(_trial(
                base_state=base_state,
                worlds=worlds,
                support_rows=support_rows,
                support_by_key=support_by_key,
                nonroot_keys=nonroot_keys,
                ambiguous_nonroot_keys=ambiguous_nonroot_keys,
                root_keys=root_keys,
                search_iterations=search_iterations,
                mccfr_iterations=mccfr_iterations,
                seed=seed,
            ))

    quality = {
        "physical_support_valid": True,
        "support_worlds_exactly_36": len(worlds) == 36,
        "reachable_support_nonempty": len(support_rows) > 0,
        "root_information_states_exactly_3": len(root_keys) == 3,
        "all_four_paired_trials_executed": len(trials) == 4,
        "all_trials_technical_pass": all(row["technical_pass"] for row in trials),
        "no_exact_best_response_used": True,
        "no_policy_completion_used": True,
        "no_uniform_missing_policy_evaluation_used": True,
        "no_strength_winner_claim": True,
        "ci_runtime_guarded_by_workflow_timeout": True,
    }
    passed = all(quality.values())

    source_paths = [
        "tools/openofc_solver/EXTERNAL_05G_BROAD_HIDDEN_INFORMATION_CONTRACT.md",
        "tools/openofc_solver/EXTERNAL_05G_Q0B_SEARCH_MCCFR_SMOKE_CONTRACT.md",
        "tools/openofc_solver/external_05g_broad_support.py",
        "tools/openofc_solver/external_hidden_discard_overlap.py",
        "tools/openofc_solver/external_hidden_discard_overlap_strategic.py",
        "tools/openofc_solver/strategic_cfr.py",
        "tools/openofc_solver/run_external_05g_q0b.py",
    ]
    payload = {
        "schema": "openofc-external-component-ab-v1",
        "experiment_id": EXPERIMENT_ID,
        "authority": AUTHORITY,
        "component": "broad-hidden-information-search-mccfr-technical-smoke",
        "config": {
            "seeds": list(SEEDS),
            "budget_pairs": [
                {"search_iterations": search, "mccfr_iterations": cfr}
                for search, cfr in BUDGET_PAIRS
            ],
            "search_exploration": 1.0,
            "support_worlds": len(worlds),
            "support_sha256": support_sha256(worlds),
        },
        "exhaustive_support": {
            "reachable_information_states": len(support_rows),
            "nonroot_information_states": len(nonroot_keys),
            "ambiguous_nonroot_information_states": len(ambiguous_nonroot_keys),
            "root_information_states": len(root_keys),
        },
        "trials": trials,
        "quality": quality,
        "verdict": "PASS_SMOKE" if passed else "BLOCK_TECHNICAL",
        "promotion_recommendation": (
            "CONTINUE_TO_05G_Q0C_PAIRED_POLICY_COMPLETENESS_ROUTER"
            if passed else
            "Q0B_FAIL_CLOSED_FIX_TECHNICAL_DEFECT_WITHOUT_MOVING_FROZEN_GATES"
        ),
        "limitations": [
            "Q0B is a technical smoke, not a strategic strength comparison",
            "coverage ratios are measurements rather than pass thresholds",
            "missing Search/MCCFR infosets remain missing and are not evaluated as uniform policy",
            "root TV distance is diagnostic only",
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
        raise RuntimeError(f"05G-Q0B technical smoke failed: {quality}")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/external_05g_q0b.json")
    args = parser.parse_args()
    payload = run()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    coverage_rows = []
    tv_values = []
    for trial in payload["trials"]:
        coverage_rows.append({
            "seed": trial["seed"],
            "search_iterations": trial["search_iterations"],
            "mccfr_iterations": trial["mccfr_iterations"],
            "search_nonroot": trial["search"]["coverage"]["nonroot_ratio"],
            "mccfr_nonroot": trial["mccfr"]["coverage"]["nonroot_ratio"],
        })
        tv_values.extend(
            row["tv_distance"]
            for row in trial["root_diagnostics"]
            if "tv_distance" in row
        )
    print(json.dumps({
        "experiment_id": payload["experiment_id"],
        "verdict": payload["verdict"],
        "reachable_information_states": payload["exhaustive_support"]["reachable_information_states"],
        "coverage": coverage_rows,
        "root_tv_min": min(tv_values) if tv_values else None,
        "root_tv_max": max(tv_values) if tv_values else None,
        "manifest_sha256": payload["sha256"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
