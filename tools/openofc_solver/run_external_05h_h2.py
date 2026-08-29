from __future__ import annotations

"""05H-H2 explicit M provenance/completion materialization.

This gate is structural only: no EV, best response, NashConv or exploitability.
"""

import argparse
import hashlib
import json
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
from external_hidden_discard_overlap_strategic import (
    OverlapExternalSamplingMCCFR,
    ReachableSupport,
    build_reachable_support,
)
from run_external_05g_q0b import _support_maps, _validate_profile
from run_external_05g_q1a import _profile_sha256, _source_map_sha256
from run_external_05g_q1b import _materialize_completion_profile
from run_external_05h_h1 import BUDGETS, SEEDS

EXPERIMENT_ID = "EXT-05H-H2-EXPLICIT-M-PROVENANCE-COMPLETION"
MCCFR_NATIVE = "MCCFR_NATIVE"

BehaviorProfile = Mapping[str, Mapping[str, float]]


def _assemble_m(
    *,
    support_rows: Sequence[ReachableSupport],
    mccfr: BehaviorProfile,
    completion: BehaviorProfile,
) -> tuple[dict[str, dict[str, float]], dict[str, str]]:
    profile: dict[str, dict[str, float]] = {}
    source: dict[str, str] = {}
    for row in support_rows:
        key = row.information_state_key
        if key in mccfr:
            dist = mccfr[key]
            label = MCCFR_NATIVE
        else:
            dist = completion[key]
            label = COMPLETION_SOURCE
        profile[key] = {action: float(prob) for action, prob in dist.items()}
        source[key] = label
    return profile, source


def _accounting(source_map: Mapping[str, str], support_rows: Sequence[ReachableSupport]) -> dict:
    allowed = (MCCFR_NATIVE, COMPLETION_SOURCE)
    if set(source_map) != {row.information_state_key for row in support_rows}:
        raise AssertionError("H2 source map must cover exhaustive support")
    counts = {label: 0 for label in allowed}
    ambiguous_nonroot = {label: 0 for label in allowed}
    by_layer: dict[str, dict[str, int]] = {}
    for row in support_rows:
        key = row.information_state_key
        label = source_map[key]
        if label not in allowed:
            raise AssertionError("H2 undeclared source label")
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


def _sha256_file(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(*, mccfr_iterations: int) -> dict:
    if mccfr_iterations not in BUDGETS:
        raise ValueError(f"H2 MCCFR budget must be one of frozen H1 budgets: {BUDGETS}")

    base_state = public_pre_r3_state()
    support = worlds()
    validate_physical_support(base_state, support)

    t0 = perf_counter()
    support_rows = build_reachable_support(base_state, support)
    support_seconds = perf_counter() - t0
    support_by_key, nonroot_keys, ambiguous_nonroot_keys, root_keys = _support_maps(support_rows)
    if len(support) != 144 or len(support_rows) != 261076:
        raise RuntimeError("H2 refuses geometry that differs from passed H0 artifact")

    t1 = perf_counter()
    completion = build_uniform_local_backward_completion(support_rows)
    completion_seconds = perf_counter() - t1
    completion_profile = _materialize_completion_profile(support_rows, completion.choice_map())
    if set(completion_profile) != set(support_by_key):
        raise AssertionError("completion profile is not exhaustive")

    world_ids = tuple(world.world_id for world in support)
    seed_results = []
    for seed in SEEDS:
        t2 = perf_counter()
        solver = OverlapExternalSamplingMCCFR(base_state, support, seed=seed)
        solver.run(mccfr_iterations)
        mccfr = solver.current_profile()
        mccfr_seconds = perf_counter() - t2
        native_validation = _validate_profile(mccfr, support_by_key, world_ids)

        m_profile, source_map = _assemble_m(
            support_rows=support_rows,
            mccfr=mccfr,
            completion=completion_profile,
        )
        m_validation = _validate_profile(m_profile, support_by_key, world_ids)
        accounting = _accounting(source_map, support_rows)

        native_preserved = all(
            source_map[key] == MCCFR_NATIVE
            and dict(m_profile[key]) == {action: float(prob) for action, prob in mccfr[key].items()}
            for key in mccfr
        )
        completion_only_in_holes = all(
            not (source_map[key] == COMPLETION_SOURCE and key in mccfr)
            for key in source_map
        )
        complete = set(m_profile) == set(support_by_key)
        source_complete = set(source_map) == set(support_by_key)
        firewalls = all(
            validation[field] == 0
            for validation in (native_validation, m_validation)
            for field in (
                "illegal_key_count",
                "action_set_mismatch_count",
                "invalid_distribution_count",
                "hidden_world_token_leakage_count",
            )
        )
        seed_pass = native_preserved and completion_only_in_holes and complete and source_complete and firewalls
        seed_results.append({
            "seed": seed,
            "mccfr_iterations": mccfr_iterations,
            "native_runtime_seconds": mccfr_seconds,
            "native_terminal_evaluations": solver.snapshot().terminal_evaluations,
            "native_information_states": len(mccfr),
            "native_profile_sha256": _profile_sha256(mccfr),
            "native_validation": native_validation,
            "m_profile_sha256": _profile_sha256(m_profile),
            "m_source_map_sha256": accounting["source_map_sha256"],
            "m_validation": m_validation,
            "source_accounting": accounting,
            "native_preserved_exactly": native_preserved,
            "completion_only_in_native_holes": completion_only_in_holes,
            "profile_complete": complete,
            "source_map_complete": source_complete,
            "seed_pass": seed_pass,
        })

    quality = {
        "support_matches_h0": len(support_rows) == 261076 and len(support) == 144,
        "completion_exhaustive": completion.information_states == len(support_rows),
        "completion_seed_independent": True,
        "both_seeds_pass": len(seed_results) == 2 and all(row["seed_pass"] for row in seed_results),
        "mccfr_budget_is_frozen_h1_candidate": mccfr_iterations in BUDGETS,
        "no_ev": True,
        "no_best_response": True,
        "no_nashconv_or_exploitability": True,
        "no_production_authority": True,
        "real_routes_certified_zero": True,
    }
    passed = all(quality.values())

    source_paths = [
        "tools/openofc_solver/EXTERNAL_05H_144_WORLD_BROADENING_CONTRACT.md",
        "tools/openofc_solver/EXTERNAL_05H_H1_MCCFR_NATIVE_COVERAGE_CONTRACT.md",
        "tools/openofc_solver/EXTERNAL_05H_H2_M_PROVENANCE_COMPLETION_CONTRACT.md",
        "tools/openofc_solver/external_05h_broad_support.py",
        "tools/openofc_solver/run_external_05h_h2.py",
    ]
    payload = {
        "schema": "openofc-external-component-ab-v1",
        "experiment_id": EXPERIMENT_ID,
        "authority": AUTHORITY,
        "component": "explicit-M-native-plus-completion-provenance-144-world-fixture",
        "config": {
            "seeds": list(SEEDS),
            "mccfr_iterations": mccfr_iterations,
            "support_sha256": support_sha256(support),
            "mccfr_source_label": MCCFR_NATIVE,
            "completion_source_label": COMPLETION_SOURCE,
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
            "rollout_cache_entries": completion.rollout_cache_entries,
            "policy_sha256": completion.policy_sha256,
            "source_label": completion.source_label,
        },
        "seed_results": seed_results,
        "quality": quality,
        "verdict": "PASS_05H_H2_M_PROVENANCE" if passed else "FAIL_05H_H2_M_PROVENANCE",
        "next_gate_recommendation": "05H_H3_EXACT_BILATERAL_BR" if passed else "STOP_AND_DIAGNOSE_H2",
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
        "config": payload["config"],
        "completion_build": payload["completion_build"],
        "seed_source_accounting": [
            {
                "seed": row["seed"],
                "native_information_states": row["native_information_states"],
                "source_accounting": row["source_accounting"],
                "m_profile_sha256": row["m_profile_sha256"],
            }
            for row in payload["seed_results"]
        ],
        "manifest_sha256": payload["manifest_sha256"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
