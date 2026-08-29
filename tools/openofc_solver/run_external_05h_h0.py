from __future__ import annotations

"""Run 05H-H0 geometry-only gate for the frozen 144-world support."""

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from time import perf_counter

from external_05h_broad_support import (
    AUTHORITY,
    private_types,
    public_pre_r3_state,
    summarize_geometry,
    validate_physical_support,
    worlds,
)
from external_hidden_discard_overlap_strategic import build_reachable_support

EXPERIMENT_ID = "EXT-05H-H0-144-WORLD-GEOMETRY"

FROZEN_05G = {
    "support_worlds": 36,
    "reachable_information_states": 69828,
    "ambiguous_nonroot_information_states": 15393,
    "nonroot_information_states_ge3_states": 10101,
    "max_compatible_states": 12,
}


def _sha256_file(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run() -> dict:
    base_state = public_pre_r3_state()
    support = worlds()

    t0 = perf_counter()
    validate_physical_support(base_state, support)
    physical_seconds = perf_counter() - t0

    t1 = perf_counter()
    support_rows = build_reachable_support(base_state, support)
    support_seconds = perf_counter() - t1

    t2 = perf_counter()
    geometry = summarize_geometry(base_state, support, support_rows=support_rows)
    geometry_seconds = perf_counter() - t2

    layer_names = {row[0] for row in geometry.layers}
    quality = {
        "exactly_144_worlds": geometry.support_worlds == 144,
        "exact_4x4x3x3_types": (
            geometry.p0_r3_private_types,
            geometry.p1_r3_private_types,
            geometry.p0_r4_private_types,
            geometry.p1_r4_private_types,
        ) == (4, 4, 3, 3),
        "all_four_decision_layers": layer_names == {"R3_P0", "R3_P1", "R4_P0", "R4_P1"},
        "hidden_discard_collision_p0": geometry.p0_hidden_discard_collision,
        "hidden_discard_collision_p1": geometry.p1_hidden_discard_collision,
        "reachable_infosets_strictly_broader_than_05g": (
            geometry.reachable_information_states > FROZEN_05G["reachable_information_states"]
        ),
        "ambiguous_nonroot_strictly_broader_than_05g": (
            geometry.ambiguous_nonroot_information_states
            > FROZEN_05G["ambiguous_nonroot_information_states"]
        ),
        "ge3_nonroot_strictly_broader_than_05g": (
            geometry.nonroot_information_states_ge3_states
            > FROZEN_05G["nonroot_information_states_ge3_states"]
        ),
        "max_compatible_states_strictly_broader_than_05g": (
            geometry.max_compatible_states > FROZEN_05G["max_compatible_states"]
        ),
        "no_payoff_evaluation": True,
        "no_search_training": True,
        "no_mccfr_training": True,
        "no_best_response": True,
        "no_production_authority": True,
        "real_routes_certified_zero": True,
    }
    passed = all(quality.values())

    type_counts = {key: len(value) for key, value in private_types().items()}
    source_paths = [
        "tools/openofc_solver/EXTERNAL_05H_144_WORLD_BROADENING_CONTRACT.md",
        "tools/openofc_solver/external_05h_broad_support.py",
        "tools/openofc_solver/run_external_05h_h0.py",
    ]
    payload = {
        "schema": "openofc-external-component-ab-v1",
        "experiment_id": EXPERIMENT_ID,
        "authority": AUTHORITY,
        "component": "geometry-only-144-world-hidden-information-broadening",
        "config": {
            "cartesian_type_counts": type_counts,
            "expected_worlds": 144,
            "selection_basis": "card_and_information_geometry_only_before_any_strategic_payoff",
        },
        "frozen_05g_reference": FROZEN_05G,
        "geometry": asdict(geometry),
        "runtime_seconds": {
            "physical_validation": physical_seconds,
            "exhaustive_support_materialization": support_seconds,
            "geometry_and_collision_summary": geometry_seconds,
            "total": physical_seconds + support_seconds + geometry_seconds,
        },
        "quality": quality,
        "verdict": "PASS_05H_H0_GEOMETRY" if passed else "FAIL_05H_H0_GEOMETRY",
        "next_gate_recommendation": (
            "05H_H1_MCCFR_NATIVE_COVERAGE_CALIBRATION"
            if passed
            else "STOP_AND_DIAGNOSE_GEOMETRY_WITHOUT_PAYOFF_BASED_SUPPORT_SELECTION"
        ),
        "real_routes_certified": 0,
        "files": [
            {"path": path, "sha256": _sha256_file(path)}
            for path in source_paths
        ],
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
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    payload = run()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "experiment_id": payload["experiment_id"],
        "verdict": payload["verdict"],
        "geometry": payload["geometry"],
        "runtime_seconds": payload["runtime_seconds"],
        "next_gate_recommendation": payload["next_gate_recommendation"],
        "manifest_sha256": payload["manifest_sha256"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
