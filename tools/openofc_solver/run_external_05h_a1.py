from __future__ import annotations

"""05H-A1 exact current-vs-simple-average MCCFR architecture comparator."""

import argparse
import hashlib
import json
import math
from pathlib import Path
from time import perf_counter
from typing import Mapping, Sequence

from external_05g_uniform_backward_completion import (
    SOURCE_LABEL as COMPLETION_SOURCE,
    build_uniform_local_backward_completion,
)
from external_05h_broad_support import (
    AUTHORITY,
    public_pre_r3_state,
    support_sha256,
    validate_physical_support,
    worlds,
)
from external_05h_mccfr_simple_average import OverlapExternalSamplingMCCFRSimpleAverage
from external_hidden_discard_overlap_strategic import ReachableSupport, build_reachable_support, exact_nash_conv
from run_external_05g_q0b import _support_maps, _validate_profile
from run_external_05g_q1a import _profile_sha256, _source_map_sha256
from run_external_05g_q1b import _materialize_completion_profile
from run_external_05g_q1c import _exact_asymmetric_value
from run_external_05g_q2 import _br_behavior_profile
from run_external_05h_h1 import BUDGETS, SEEDS
from run_external_05h_h3 import LOW_NOT_STRICT_MAX, REPLAY_TOLERANCE, STRICT_NEAR_NASH, _band

EXPERIMENT_ID = "EXT-05H-A1-MCCFR-CURRENT-VS-SIMPLE-AVERAGE-EXACT-BR"
COMPARE_TOLERANCE = 1e-9
CURRENT_NATIVE = "MCCFR_CURRENT_NATIVE"
AVERAGE_NATIVE = "MCCFR_SIMPLE_AVERAGE_NATIVE"

BehaviorProfile = Mapping[str, Mapping[str, float]]


def _complete_candidate(
    *,
    native_label: str,
    support_rows: Sequence[ReachableSupport],
    native: BehaviorProfile,
    completion: BehaviorProfile,
) -> tuple[dict[str, dict[str, float]], dict[str, str]]:
    profile: dict[str, dict[str, float]] = {}
    source: dict[str, str] = {}
    for row in support_rows:
        key = row.information_state_key
        if key in native:
            profile[key] = {action: float(prob) for action, prob in native[key].items()}
            source[key] = native_label
        else:
            profile[key] = {action: float(prob) for action, prob in completion[key].items()}
            source[key] = COMPLETION_SOURCE
    return profile, source


def _source_accounting(
    *,
    native_label: str,
    source_map: Mapping[str, str],
    support_rows: Sequence[ReachableSupport],
) -> dict:
    allowed = (native_label, COMPLETION_SOURCE)
    counts = {label: 0 for label in allowed}
    ambiguous_nonroot = {label: 0 for label in allowed}
    by_layer: dict[str, dict[str, int]] = {}
    for row in support_rows:
        label = source_map[row.information_state_key]
        if label not in allowed:
            raise AssertionError("A1 source map contains undeclared label")
        counts[label] += 1
        layer = f"R{row.round_index}_P{row.actor}"
        bucket = by_layer.setdefault(layer, {name: 0 for name in allowed})
        bucket[label] += 1
        if (row.round_index, row.actor) != (3, 0) and len(row.concrete_states) > 1:
            ambiguous_nonroot[label] += 1
    total = len(support_rows)
    return {
        "counts": counts,
        "percentages": {label: counts[label] / total for label in allowed},
        "counts_by_layer": {layer: by_layer[layer] for layer in sorted(by_layer)},
        "ambiguous_nonroot_counts": ambiguous_nonroot,
        "source_map_sha256": _source_map_sha256(source_map),
    }


def _evaluate_exact(
    *,
    profile_name: str,
    profile: BehaviorProfile,
    base_state,
    support,
    support_rows: Sequence[ReachableSupport],
) -> dict:
    t0 = perf_counter()
    nash = exact_nash_conv(base_state, support, profile=profile, support_rows=support_rows)
    br_seconds = perf_counter() - t0

    br0_choices = nash.br0.choice_map()
    br1_choices = nash.br1.choice_map()
    br0_profile = _br_behavior_profile(support_rows, player=0, choices=br0_choices)
    br1_profile = _br_behavior_profile(support_rows, player=1, choices=br1_choices)

    t1 = perf_counter()
    br0_replay = _exact_asymmetric_value(
        base_state,
        support,
        p0_profile=br0_profile,
        p1_profile=profile,
    )
    br1_replay = _exact_asymmetric_value(
        base_state,
        support,
        p0_profile=profile,
        p1_profile=br1_profile,
    )
    replay_seconds = perf_counter() - t1

    br0_error = abs(br0_replay["expected_u0"] - nash.br0.value)
    br1_error = abs((-br1_replay["expected_u0"]) - nash.br1.value)
    expected0 = sum(1 for row in support_rows if row.actor == 0)
    expected1 = sum(1 for row in support_rows if row.actor == 1)
    coverage_pass = len(br0_choices) == expected0 and len(br1_choices) == expected1
    replay_pass = (
        br0_replay["missing_profile_lookups"] == 0
        and br1_replay["missing_profile_lookups"] == 0
        and br0_error <= REPLAY_TOLERANCE
        and br1_error <= REPLAY_TOLERANCE
    )
    finite_pass = all(math.isfinite(value) for value in (
        nash.br0.value, nash.br1.value, nash.nash_conv, nash.exploitability
    ))
    nonnegative_pass = nash.nash_conv >= -REPLAY_TOLERANCE
    return {
        "profile": profile_name,
        "br0_value": nash.br0.value,
        "br1_value": nash.br1.value,
        "nash_conv": nash.nash_conv,
        "exploitability": nash.exploitability,
        "interpretation_band": _band(nash.exploitability),
        "best_response_runtime_seconds": br_seconds,
        "exact_replay_runtime_seconds": replay_seconds,
        "br0_absolute_replay_error": br0_error,
        "br1_absolute_replay_error": br1_error,
        "br0_terminal_leaves": nash.br0.terminal_leaves,
        "br1_terminal_leaves": nash.br1.terminal_leaves,
        "coverage_pass": coverage_pass,
        "replay_pass": replay_pass,
        "finite_pass": finite_pass,
        "nonnegative_nashconv_pass": nonnegative_pass,
        "evaluation_pass": coverage_pass and replay_pass and finite_pass and nonnegative_pass,
    }


def _order(current: float, average: float) -> str:
    if average + COMPARE_TOLERANCE < current:
        return "AVERAGE_LOWER"
    if current + COMPARE_TOLERANCE < average:
        return "CURRENT_LOWER"
    return "TIED_WITHIN_1E-9"


def _sha256_file(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(*, mccfr_iterations: int) -> dict:
    if mccfr_iterations not in BUDGETS:
        raise ValueError(f"A1 budget must be frozen H1 candidate: {BUDGETS}")

    base_state = public_pre_r3_state()
    support = worlds()
    validate_physical_support(base_state, support)

    t_support = perf_counter()
    support_rows = build_reachable_support(base_state, support)
    support_seconds = perf_counter() - t_support
    support_by_key, nonroot_keys, ambiguous_nonroot_keys, root_keys = _support_maps(support_rows)
    if len(support) != 144 or len(support_rows) != 261076:
        raise RuntimeError("A1 refuses geometry differing from passed H0")

    t_completion = perf_counter()
    completion = build_uniform_local_backward_completion(support_rows)
    completion_seconds = perf_counter() - t_completion
    completion_profile = _materialize_completion_profile(support_rows, completion.choice_map())
    world_ids = tuple(world.world_id for world in support)

    seed_results = []
    for seed in SEEDS:
        t_train = perf_counter()
        solver = OverlapExternalSamplingMCCFRSimpleAverage(base_state, support, seed=seed)
        solver.run(mccfr_iterations)
        training_seconds = perf_counter() - t_train
        current_native = solver.current_profile()
        average_native = solver.average_profile()

        native_validation = {
            "current": _validate_profile(current_native, support_by_key, world_ids),
            "average": _validate_profile(average_native, support_by_key, world_ids),
        }

        candidates = {}
        for candidate_name, native_label, native in (
            ("M_current", CURRENT_NATIVE, current_native),
            ("M_average", AVERAGE_NATIVE, average_native),
        ):
            profile, source_map = _complete_candidate(
                native_label=native_label,
                support_rows=support_rows,
                native=native,
                completion=completion_profile,
            )
            validation = _validate_profile(profile, support_by_key, world_ids)
            accounting = _source_accounting(
                native_label=native_label,
                source_map=source_map,
                support_rows=support_rows,
            )
            native_preserved = all(
                source_map[key] == native_label
                and dict(profile[key]) == {action: float(prob) for action, prob in native[key].items()}
                for key in native
            )
            complete = set(profile) == set(support_by_key) and set(source_map) == set(support_by_key)
            firewalls = complete and native_preserved and all(
                validation[field] == 0
                for field in (
                    "illegal_key_count",
                    "action_set_mismatch_count",
                    "invalid_distribution_count",
                    "hidden_world_token_leakage_count",
                )
            )
            if not firewalls:
                raise RuntimeError(f"A1 {candidate_name} profile failed structural firewall")

            exact = _evaluate_exact(
                profile_name=candidate_name,
                profile=profile,
                base_state=base_state,
                support=support,
                support_rows=support_rows,
            )
            candidates[candidate_name] = {
                "native_information_states": len(native),
                "native_profile_sha256": _profile_sha256(native),
                "complete_profile_sha256": _profile_sha256(profile),
                "source_map_sha256": accounting["source_map_sha256"],
                "source_accounting": accounting,
                "profile_validation": validation,
                "native_preserved_exactly": native_preserved,
                "complete_profile_firewall_pass": firewalls,
                "exact": exact,
            }

        current_e = float(candidates["M_current"]["exact"]["exploitability"])
        average_e = float(candidates["M_average"]["exact"]["exploitability"])
        order = _order(current_e, average_e)
        native_firewalls = all(
            validation[field] == 0
            for validation in native_validation.values()
            for field in (
                "illegal_key_count",
                "action_set_mismatch_count",
                "invalid_distribution_count",
                "hidden_world_token_leakage_count",
            )
        )
        seed_results.append({
            "seed": seed,
            "mccfr_iterations": mccfr_iterations,
            "training_runtime_seconds": training_seconds,
            "solver_snapshot": {
                "iterations": solver.average_snapshot().iterations,
                "regret_information_states": solver.average_snapshot().regret_information_states,
                "average_information_states": solver.average_snapshot().average_information_states,
                "terminal_evaluations": solver.average_snapshot().terminal_evaluations,
                "average_policy_updates": solver.average_snapshot().average_policy_updates,
            },
            "native_validation": native_validation,
            "candidates": candidates,
            "exploitability_order": order,
            "exploitability_difference_average_minus_current": average_e - current_e,
            "seed_pass": native_firewalls and all(
                candidate["exact"]["evaluation_pass"]
                for candidate in candidates.values()
            ),
        })

    orders = [row["exploitability_order"] for row in seed_results]
    if len(orders) == 2 and all(value == "AVERAGE_LOWER" for value in orders):
        cross_seed = "AVERAGE_LOWER_REPLICATED"
    elif len(orders) == 2 and all(value == "CURRENT_LOWER" for value in orders):
        cross_seed = "CURRENT_LOWER_REPLICATED"
    elif len(orders) == 2 and all(value == "TIED_WITHIN_1E-9" for value in orders):
        cross_seed = "TIED_REPLICATED"
    else:
        cross_seed = "NO_REPLICATED_EXPLOITABILITY_ORDER"

    architecture_quality = {}
    for candidate_name in ("M_current", "M_average"):
        bands = [row["candidates"][candidate_name]["exact"]["interpretation_band"] for row in seed_results]
        architecture_quality[candidate_name] = {
            "per_seed_bands": bands,
            "strict_near_nash_replicated": len(bands) == 2 and all(band == "NEAR_NASH_STRICT" for band in bands),
            "low_or_better_replicated": len(bands) == 2 and all(
                band in {"NEAR_NASH_STRICT", "LOW_BUT_NOT_STRICT"} for band in bands
            ),
        }

    quality = {
        "support_matches_h0": len(support) == 144 and len(support_rows) == 261076,
        "completion_complete": completion.information_states == len(support_rows),
        "both_seeds_separate": len(seed_results) == 2 and [row["seed"] for row in seed_results] == list(SEEDS),
        "both_seeds_mechanical_pass": len(seed_results) == 2 and all(row["seed_pass"] for row in seed_results),
        "comparison_tolerance_frozen": COMPARE_TOLERANCE == 1e-9,
        "h3_quality_bands_reused_without_change": STRICT_NEAR_NASH == 1e-6 and LOW_NOT_STRICT_MAX == 1e-3,
        "no_cross_seed_average_for_winner": True,
        "no_production_authority": True,
        "real_routes_certified_zero": True,
    }
    passed = all(quality.values())

    source_paths = [
        "docs/OFC_MCCFR_CURRENT_VS_AVERAGE_STRATEGY_LITERATURE_AUDIT_2026-08-29.md",
        "tools/openofc_solver/EXTERNAL_05H_A0_MCCFR_AVERAGE_FIDELITY_CONTRACT.md",
        "tools/openofc_solver/EXTERNAL_05H_A1_CURRENT_VS_AVERAGE_EXACT_BR_CONTRACT.md",
        "tools/openofc_solver/external_05h_mccfr_simple_average.py",
        "tools/openofc_solver/run_external_05h_a1.py",
    ]
    payload = {
        "schema": "openofc-external-component-ab-v1",
        "experiment_id": EXPERIMENT_ID,
        "authority": AUTHORITY,
        "component": "current-vs-simple-average-external-sampling-MCCFR-exact-BR-comparator",
        "config": {
            "seeds": list(SEEDS),
            "mccfr_iterations": mccfr_iterations,
            "support_sha256": support_sha256(support),
            "comparison_tolerance": COMPARE_TOLERANCE,
            "replay_tolerance": REPLAY_TOLERANCE,
            "strict_near_nash_threshold": STRICT_NEAR_NASH,
            "low_not_strict_threshold": LOW_NOT_STRICT_MAX,
        },
        "exhaustive_support": {
            "chance_worlds": len(support),
            "reachable_information_states": len(support_rows),
            "root_information_states": len(root_keys),
            "nonroot_information_states": len(nonroot_keys),
            "ambiguous_nonroot_information_states": len(ambiguous_nonroot_keys),
            "support_materialization_runtime_seconds": support_seconds,
        },
        "completion_build": {
            "runtime_seconds": completion_seconds,
            "information_states": completion.information_states,
            "terminal_evaluations": completion.terminal_evaluations,
            "policy_sha256": completion.policy_sha256,
        },
        "seed_results": seed_results,
        "cross_seed_exploitability_order": cross_seed,
        "architecture_quality": architecture_quality,
        "quality": quality,
        "verdict": "PASS_05H_A1_CURRENT_VS_AVERAGE_EXACT_BR" if passed else "FAIL_05H_A1_CURRENT_VS_AVERAGE_EXACT_BR",
        "real_routes_certified": 0,
        "files": [{"path": path, "sha256": _sha256_file(path)} for path in source_paths],
    }
    payload["manifest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()
    if not passed:
        raise RuntimeError(json.dumps({
            "experiment_id": EXPERIMENT_ID,
            "verdict": payload["verdict"],
            "quality": quality,
            "manifest_sha256": payload["manifest_sha256"],
        }, sort_keys=True))
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mccfr-iterations", required=True, type=int)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    payload = run(mccfr_iterations=args.mccfr_iterations)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "experiment_id": payload["experiment_id"],
        "verdict": payload["verdict"],
        "cross_seed_exploitability_order": payload["cross_seed_exploitability_order"],
        "architecture_quality": payload["architecture_quality"],
        "seed_summaries": [
            {
                "seed": row["seed"],
                "order": row["exploitability_order"],
                "current_exploitability": row["candidates"]["M_current"]["exact"]["exploitability"],
                "average_exploitability": row["candidates"]["M_average"]["exact"]["exploitability"],
                "average_minus_current": row["exploitability_difference_average_minus_current"],
                "current_native": row["candidates"]["M_current"]["native_information_states"],
                "average_native": row["candidates"]["M_average"]["native_information_states"],
            }
            for row in payload["seed_results"]
        ],
        "manifest_sha256": payload["manifest_sha256"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
