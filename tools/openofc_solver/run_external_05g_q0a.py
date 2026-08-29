from __future__ import annotations

"""Run 05G-Q0A deterministic support-geometry gate.

Q0A deliberately stops before Search/MCCFR strategy quality.  It may inspect
only physical support and information-set geometry, matching the precommitted
05G anti-cherry-picking rule.
"""

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from external_05g_broad_support import (
    AUTHORITY,
    broad_worlds,
    public_pre_r3_state,
    summarize_geometry,
)
from external_hidden_discard_overlap_strategic import build_reachable_support

EXPERIMENT_ID = "EXT-05G-Q0A-BROAD-HIDDEN-INFORMATION-GEOMETRY"


def run() -> dict:
    worlds = broad_worlds()
    base = public_pre_r3_state()
    rows = build_reachable_support(base, worlds)
    geometry = summarize_geometry(base, worlds, support_rows=rows)

    quality = {
        "support_at_least_18_worlds": geometry.support_worlds >= 18,
        "p0_r3_at_least_3_private_types": geometry.p0_r3_private_types >= 3,
        "p1_r3_at_least_3_private_types": geometry.p1_r3_private_types >= 3,
        "p0_r4_at_least_2_private_types": geometry.p0_r4_private_types >= 2,
        "p1_r4_at_least_2_private_types": geometry.p1_r4_private_types >= 2,
        "at_least_1000_nonroot_ambiguous_infosets": geometry.ambiguous_nonroot_information_states >= 1_000,
        "at_least_100_nonroot_infosets_with_ge3_worlds": geometry.nonroot_information_states_ge3_worlds >= 100,
        "p0_hidden_discard_collision": geometry.p0_hidden_discard_collision,
        "p1_hidden_discard_collision": geometry.p1_hidden_discard_collision,
        "no_payoff_based_selection": True,
        "no_certification_claim": True,
    }

    source_paths = [
        "tools/openofc_solver/EXTERNAL_05G_BROAD_HIDDEN_INFORMATION_CONTRACT.md",
        "tools/openofc_solver/external_05g_broad_support.py",
        "tools/openofc_solver/test_external_05g_broad_support.py",
        "tools/openofc_solver/run_external_05g_q0a.py",
        "tools/openofc_solver/external_hidden_discard_overlap.py",
        "tools/openofc_solver/external_hidden_discard_overlap_strategic.py",
        "tools/openofc_solver/strategic_cfr.py",
    ]
    payload = {
        "schema": "openofc-external-component-ab-v1",
        "experiment_id": EXPERIMENT_ID,
        "authority": AUTHORITY,
        "component": "broad-hidden-information-support-geometry",
        "construction": {
            "selection_uses_terminal_utility": False,
            "selection_uses_best_response": False,
            "selection_uses_search_performance": False,
            "selection_uses_mccfr_performance": False,
            "cartesian_private_type_schedule": "3x3x2x2",
        },
        "geometry": asdict(geometry),
        "quality": quality,
        "files": [
            {"path": path, "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}
            for path in source_paths
        ],
        "limitations": [
            "Q0A validates support and information geometry only",
            "Search and MCCFR smoke are intentionally deferred to Q0B after geometry passes",
            "no terminal payoff is used to accept or reject the support",
            "finite reduced game only",
            "not production certification",
        ],
        "promotion_recommendation": "CONTINUE_TO_05G_Q0B_SEARCH_AND_MCCFR_SMOKE" if all(quality.values()) else "Q0A_FAIL_CLOSED_DO_NOT_RELAX_GATES",
        "real_routes_certified": 0,
    }
    if not all(quality.values()):
        raise RuntimeError(f"05G-Q0A geometry gate failed: {quality}; geometry={asdict(geometry)}")
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    payload["sha256"] = hashlib.sha256(raw).hexdigest()
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/external_05g_q0a.json")
    args = parser.parse_args()
    payload = run()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    geometry = payload["geometry"]
    print(json.dumps({
        "experiment_id": payload["experiment_id"],
        "support_worlds": geometry["support_worlds"],
        "reachable_information_states": geometry["reachable_information_states"],
        "ambiguous_nonroot_information_states": geometry["ambiguous_nonroot_information_states"],
        "nonroot_information_states_ge3_worlds": geometry["nonroot_information_states_ge3_worlds"],
        "max_compatible_worlds": geometry["max_compatible_worlds"],
        "support_sha256": geometry["support_sha256"],
        "manifest_sha256": payload["sha256"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
