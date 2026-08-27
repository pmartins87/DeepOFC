from __future__ import annotations

"""Quantify practical usefulness of the classical External Sampling MCCFR bound.

The pilot is analytical once each reduced game's exact infoset/action structure is
constructed. It performs no sampled training and makes no production claim.
"""

import hashlib
import json
from pathlib import Path

from deepofc.hu_two_round_hidden_discard import HUTwoRoundHiddenDiscardSubgame
from deepofc.hu_two_round_joker import HUTwoRoundJokerSubgame
from m5p_external_sampling_theoretical_bound import (
    AUTHORITY as BOUND_AUTHORITY,
    external_sampling_theoretical_bound,
    project_raw_pairwise_utility_range,
    required_iterations_for_exploitability,
)

SCHEMA = "openofc-m5p-external-sampling-theorem-feasibility-pilot-v1"
AUTHORITY = "CLASSICAL_EXTERNAL_SAMPLING_BOUND_FEASIBILITY_PILOT_NOT_CERTIFICATION"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "m5p_external_sampling_theoretical_bound.json"
OVERALL_FAILURE_PROBABILITY = 0.05
PROBE_ITERATIONS = 1_000_000
TARGETS = (1.0, 0.25, 0.15, 0.05)
UTILITY_RANGES = (1.0, project_raw_pairwise_utility_range())


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _source_manifest() -> dict[str, object]:
    paths = (
        "deepofc/hu_two_round.py",
        "deepofc/hu_two_round_hidden_discard.py",
        "deepofc/hu_two_round_joker.py",
        "deepofc/scoring.py",
        "tools/openofc_solver/M5P_EXTERNAL_SAMPLING_THEORETICAL_BOUND_CONTRACT.md",
        "tools/openofc_solver/m5p_external_sampling_theoretical_bound.py",
        "tools/openofc_solver/run_m5p_external_sampling_theoretical_bound.py",
        "tools/openofc_solver/test_m5p_external_sampling_theoretical_bound.py",
    )
    rows = [
        {
            "path": rel,
            "sha256": hashlib.sha256((ROOT / rel).read_bytes()).hexdigest(),
        }
        for rel in paths
    ]
    payload: dict[str, object] = {"files": rows}
    payload["sha256"] = _sha(payload)
    return payload


def _family_row(family_id: str, game) -> dict[str, object]:
    unit_probe = external_sampling_theoretical_bound(
        game,
        iterations=PROBE_ITERATIONS,
        overall_failure_probability=OVERALL_FAILURE_PROBABILITY,
        utility_range=1.0,
    )
    raw_probe = external_sampling_theoretical_bound(
        game,
        iterations=PROBE_ITERATIONS,
        overall_failure_probability=OVERALL_FAILURE_PROBABILITY,
        utility_range=project_raw_pairwise_utility_range(),
    )
    requirements: dict[str, dict[str, int]] = {}
    for utility_range in UTILITY_RANGES:
        label = "unit" if utility_range == 1.0 else "project_raw_206"
        requirements[label] = {
            str(target): required_iterations_for_exploitability(
                game,
                target_exploitability=target,
                overall_failure_probability=OVERALL_FAILURE_PROBABILITY,
                utility_range=utility_range,
            )
            for target in TARGETS
        }
    return {
        "family_id": family_id,
        "bound_authority": BOUND_AUTHORITY,
        "joint_confidence": unit_probe.joint_confidence,
        "per_player_failure_probability": unit_probe.per_player_failure_probability,
        "player0_structure": unit_probe.player0.payload(),
        "player1_structure": unit_probe.player1.payload(),
        "exploitability_coefficient_per_unit_utility_range": unit_probe.exploitability_coefficient_per_unit_utility_range,
        "probe_iterations": PROBE_ITERATIONS,
        "unit_range_probe_exploitability_upper_bound": unit_probe.exploitability_upper_bound,
        "raw_206_probe_exploitability_upper_bound": raw_probe.exploitability_upper_bound,
        "required_iterations": requirements,
        "production_certification_eligible": False,
    }


def main() -> None:
    rows = [
        _family_row("joker", HUTwoRoundJokerSubgame()),
        _family_row("hidden-discard", HUTwoRoundHiddenDiscardSubgame()),
    ]
    payload: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "overall_failure_probability": OVERALL_FAILURE_PROBABILITY,
        "joint_confidence": 1.0 - OVERALL_FAILURE_PROBABILITY,
        "probe_iterations": PROBE_ITERATIONS,
        "targets": list(TARGETS),
        "utility_ranges": list(UTILITY_RANGES),
        "source_manifest": _source_manifest(),
        "rows": rows,
        "summary": {
            "families": [row["family_id"] for row in rows],
            "rows": len(rows),
            "max_unit_range_iterations_for_0_15": max(
                int(row["required_iterations"]["unit"]["0.15"]) for row in rows
            ),
            "min_unit_range_iterations_for_0_15": min(
                int(row["required_iterations"]["unit"]["0.15"]) for row in rows
            ),
            "max_raw_206_iterations_for_0_15": max(
                int(row["required_iterations"]["project_raw_206"]["0.15"])
                for row in rows
            ),
            "production_certification_eligible": False,
            "data_dependent_bound_tested": False,
        },
    }
    payload["sha256"] = _sha(payload)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "artifact": str(OUT.relative_to(ROOT)),
                "sha256": payload["sha256"],
                "summary": payload["summary"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
