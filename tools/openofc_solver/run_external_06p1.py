from __future__ import annotations

"""06P1 exact reduced-game strength/compute frontier.

This runner deliberately reuses the certified 05G support, completion and exact
bilateral-BR evaluator. Candidate training cost is measured separately from the
exact audit cost so the resulting frontier answers the practical engineering
question: how much reduced-game strength does each learner buy per unit compute?
"""

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
from statistics import mean
from time import perf_counter

from external_05g_broad_support import (
    broad_worlds,
    public_pre_r3_state,
    support_sha256,
    validate_broad_physical_support,
)
from external_05g_uniform_backward_completion import build_uniform_local_backward_completion
from external_hidden_discard_overlap import run_overlap_infoset_uct
from external_hidden_discard_overlap_strategic import (
    OverlapExternalSamplingMCCFR,
    build_reachable_support,
    visit_profile_from_overlap_search,
)
from run_external_05g_q0b import _support_maps, _validate_profile
from run_external_05g_q1a import _profile_sha256
from run_external_05g_q1b import _assemble_completed, _materialize_completion_profile
from run_external_05g_q2 import _evaluate_profile

EXPERIMENT_ID = "EXT-06P1-EXACT-STRENGTH-COMPUTE-FRONTIER"
AUTHORITY = "REDUCED_GAME_EXACT_STRENGTH_COMPUTE_CALIBRATION_ONLY"
SEEDS = (20260829, 20260830)
SEARCH_BUDGETS = (1_000, 5_000, 20_000, 50_000)
MCCFR_BUDGETS = (64, 256, 1_024)
SEARCH_EXPLORATION = 1.0
TOLERANCE = 1e-9
EXPECTED_WORLDS = 36
EXPECTED_INFOSETS = 69_828
EXPECTED_NONROOT = 69_825
EXPECTED_AMBIGUOUS_NONROOT = 15_393
EXPECTED_ROOTS = 3


def _validation_pass(validation: dict) -> bool:
    return all(
        validation[field] == 0
        for field in (
            "illegal_key_count",
            "action_set_mismatch_count",
            "invalid_distribution_count",
            "hidden_world_token_leakage_count",
        )
    )


def _source_counts(source_map: dict[str, str]) -> dict[str, int]:
    counts = Counter(source_map.values())
    return {key: int(counts[key]) for key in sorted(counts)}


def _candidate_point(
    *,
    family: str,
    budget: int,
    seed: int,
    base_state,
    worlds,
    support_rows,
    support_by_key,
    completion_profile,
    baseline_exploitability: float,
) -> dict:
    if family == "SEARCH":
        t0 = perf_counter()
        result = run_overlap_infoset_uct(
            base_state,
            worlds,
            iterations=budget,
            seed=seed,
            exploration=SEARCH_EXPLORATION,
        )
        native = visit_profile_from_overlap_search(result)
        training_seconds = perf_counter() - t0
        complete, source_map = _assemble_completed(
            mode="S",
            support_rows=support_rows,
            search=native,
            mccfr={},
            completion=completion_profile,
        )
    elif family == "MCCFR":
        t0 = perf_counter()
        solver = OverlapExternalSamplingMCCFR(base_state, worlds, seed=seed)
        solver.run(budget)
        native = solver.current_profile()
        training_seconds = perf_counter() - t0
        complete, source_map = _assemble_completed(
            mode="M",
            support_rows=support_rows,
            search={},
            mccfr=native,
            completion=completion_profile,
        )
    else:
        raise ValueError(family)

    validation = _validate_profile(
        complete,
        support_by_key,
        tuple(world.world_id for world in worlds),
    )
    complete_coverage = set(complete) == set(support_by_key)
    exact = _evaluate_profile(
        name=f"{family}_{budget}_seed{seed}",
        profile=complete,
        base_state=base_state,
        worlds=worlds,
        support_rows=support_rows,
    )
    point_pass = (
        complete_coverage
        and _validation_pass(validation)
        and exact["profile_pass"]
        and math.isfinite(training_seconds)
        and training_seconds >= 0.0
    )
    return {
        "family": family,
        "budget": budget,
        "seed": seed,
        "training_seconds": training_seconds,
        "native_information_states": len(native),
        "completion_information_states": sum(
            1 for label in source_map.values() if label.startswith("COMPLETION_")
        ),
        "source_counts": _source_counts(source_map),
        "complete_profile_sha256": _profile_sha256(complete),
        "validation": validation,
        "complete_profile_100pct": complete_coverage,
        "exploitability": exact["exploitability"],
        "nash_conv": exact["nash_conv"],
        "br0_value": exact["br0"]["value"],
        "br1_value": exact["br1"]["value"],
        "exact_evaluation_seconds": exact["runtime_seconds"],
        "exact_profile_pass": exact["profile_pass"],
        "exploitability_reduction_vs_completion_only": (
            baseline_exploitability - exact["exploitability"]
        ),
        "point_pass": point_pass,
    }


def _pareto(points: list[dict]) -> dict:
    nondominated = []
    dominance = []
    for point in points:
        dominated_by = []
        for other in points:
            if other is point:
                continue
            time_no_worse = other["training_seconds"] <= point["training_seconds"]
            exploit_no_worse = other["exploitability"] <= point["exploitability"] + TOLERANCE
            strict = (
                other["training_seconds"] < point["training_seconds"]
                or other["exploitability"] + TOLERANCE < point["exploitability"]
            )
            if time_no_worse and exploit_no_worse and strict:
                dominated_by.append({
                    "family": other["family"],
                    "budget": other["budget"],
                })
        row = {
            "family": point["family"],
            "budget": point["budget"],
            "training_seconds": point["training_seconds"],
            "exploitability": point["exploitability"],
            "dominated_by": dominated_by,
        }
        dominance.append(row)
        if not dominated_by:
            nondominated.append(row)
    nondominated.sort(key=lambda row: (row["training_seconds"], row["exploitability"], row["family"], row["budget"]))
    return {
        "nondominated": nondominated,
        "all_points": dominance,
    }


def run() -> dict:
    started = perf_counter()
    worlds = broad_worlds()
    base_state = public_pre_r3_state()
    validate_broad_physical_support(base_state, worlds)
    support_rows = build_reachable_support(base_state, worlds)
    support_by_key, nonroot_keys, ambiguous_nonroot_keys, root_keys = _support_maps(support_rows)

    geometry_exact = (
        len(worlds) == EXPECTED_WORLDS
        and len(support_rows) == EXPECTED_INFOSETS
        and len(nonroot_keys) == EXPECTED_NONROOT
        and len(ambiguous_nonroot_keys) == EXPECTED_AMBIGUOUS_NONROOT
        and len(root_keys) == EXPECTED_ROOTS
    )

    t0 = perf_counter()
    completion = build_uniform_local_backward_completion(support_rows)
    completion_seconds = perf_counter() - t0
    completion_profile = _materialize_completion_profile(support_rows, completion.choice_map())
    completion_validation = _validate_profile(
        completion_profile,
        support_by_key,
        tuple(world.world_id for world in worlds),
    )
    completion_complete = set(completion_profile) == set(support_by_key)
    completion_eval = _evaluate_profile(
        name="COMPLETION_ONLY",
        profile=completion_profile,
        base_state=base_state,
        worlds=worlds,
        support_rows=support_rows,
    )
    completion_pass = (
        completion_complete
        and _validation_pass(completion_validation)
        and completion_eval["profile_pass"]
    )

    seed_results = []
    for seed in SEEDS:
        points: list[dict] = []
        for budget in SEARCH_BUDGETS:
            points.append(_candidate_point(
                family="SEARCH",
                budget=budget,
                seed=seed,
                base_state=base_state,
                worlds=worlds,
                support_rows=support_rows,
                support_by_key=support_by_key,
                completion_profile=completion_profile,
                baseline_exploitability=completion_eval["exploitability"],
            ))
        for budget in MCCFR_BUDGETS:
            points.append(_candidate_point(
                family="MCCFR",
                budget=budget,
                seed=seed,
                base_state=base_state,
                worlds=worlds,
                support_rows=support_rows,
                support_by_key=support_by_key,
                completion_profile=completion_profile,
                baseline_exploitability=completion_eval["exploitability"],
            ))
        seed_results.append({
            "seed": seed,
            "points": points,
            "pareto": _pareto(points),
            "seed_pass": len(points) == 7 and all(point["point_pass"] for point in points),
        })

    all_points = [point for row in seed_results for point in row["points"]]
    descriptive = {}
    for family, budgets in (("SEARCH", SEARCH_BUDGETS), ("MCCFR", MCCFR_BUDGETS)):
        descriptive[family] = {}
        for budget in budgets:
            rows = [
                point for point in all_points
                if point["family"] == family and point["budget"] == budget
            ]
            descriptive[family][str(budget)] = {
                "mean_training_seconds": mean(point["training_seconds"] for point in rows),
                "mean_exploitability": mean(point["exploitability"] for point in rows),
                "mean_native_information_states": mean(point["native_information_states"] for point in rows),
                "descriptive_only": True,
            }

    quality = {
        "geometry_exact": geometry_exact,
        "completion_profile_pass": completion_pass,
        "candidate_point_count_14": len(all_points) == 14,
        "both_seeds_pass": len(seed_results) == 2 and all(row["seed_pass"] for row in seed_results),
        "all_candidate_profiles_complete": all(point["complete_profile_100pct"] for point in all_points),
        "all_exact_profiles_pass": all(point["exact_profile_pass"] for point in all_points),
        "all_finite_nonnegative_exploitability": all(
            math.isfinite(point["exploitability"])
            and point["exploitability"] >= -TOLERANCE
            and math.isfinite(point["nash_conv"])
            and point["nash_conv"] >= -TOLERANCE
            for point in all_points
        ),
        "seeds_kept_separate_for_frontier": [row["seed"] for row in seed_results] == list(SEEDS),
        "exact_evaluation_cost_excluded_from_training_frontier": True,
        "real_routes_certified_zero": True,
    }
    passed = all(quality.values())

    payload = {
        "schema": "openofc-external-06p1-v1",
        "experiment_id": EXPERIMENT_ID,
        "authority": AUTHORITY,
        "frozen": {
            "seeds": list(SEEDS),
            "search_budgets": list(SEARCH_BUDGETS),
            "search_exploration": SEARCH_EXPLORATION,
            "mccfr_budgets": list(MCCFR_BUDGETS),
            "pareto_tolerance": TOLERANCE,
            "support_worlds": len(worlds),
            "support_sha256": support_sha256(worlds),
        },
        "geometry": {
            "reachable_information_states": len(support_rows),
            "nonroot_information_states": len(nonroot_keys),
            "ambiguous_nonroot_information_states": len(ambiguous_nonroot_keys),
            "root_information_states": len(root_keys),
        },
        "completion_only": {
            "build_seconds": completion_seconds,
            "policy_sha256": completion.policy_sha256,
            "validation": completion_validation,
            "complete_100pct": completion_complete,
            "exploitability": completion_eval["exploitability"],
            "nash_conv": completion_eval["nash_conv"],
            "exact_evaluation_seconds": completion_eval["runtime_seconds"],
            "profile_pass": completion_eval["profile_pass"],
        },
        "seed_results": seed_results,
        "descriptive_cross_seed": descriptive,
        "quality": quality,
        "verdict": (
            "PASS_06P1_EXACT_STRENGTH_COMPUTE_FRONTIER"
            if passed else "FAIL_06P1_STRENGTH_COMPUTE_MECHANICS"
        ),
        "interpretation": (
            "USE_PARETO_FRONTIERS_TO_ALLOCATE_METHODS_BY_GAME_REGION_NOT_AS_GLOBAL_SOLVER_AUTHORITY"
            if passed else "REPAIR_MECHANICS_WITHOUT_CHANGING_FROZEN_BUDGETS"
        ),
        "real_routes_certified": 0,
        "runtime_seconds": perf_counter() - started,
    }
    payload["manifest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()
    if not passed:
        raise RuntimeError(json.dumps({
            "experiment_id": EXPERIMENT_ID,
            "verdict": payload["verdict"],
            "quality": quality,
        }, sort_keys=True))
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/external_06p1.json")
    args = parser.parse_args()
    payload = run()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "experiment_id": payload["experiment_id"],
        "verdict": payload["verdict"],
        "completion_only_exploitability": payload["completion_only"]["exploitability"],
        "pareto": [
            {"seed": row["seed"], "nondominated": row["pareto"]["nondominated"]}
            for row in payload["seed_results"]
        ],
        "manifest_sha256": payload["manifest_sha256"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
