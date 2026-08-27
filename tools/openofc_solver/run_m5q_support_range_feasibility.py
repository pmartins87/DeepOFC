from __future__ import annotations

"""Run the precommitted M5Q exact support/range feasibility pilot."""

import hashlib
import json
from pathlib import Path

from deepofc.hu_two_round_hidden_discard import HUTwoRoundHiddenDiscardSubgame
from deepofc.hu_two_round_joker import HUTwoRoundJokerSubgame
from deepofc.hu_two_round_mccfr import TwoRoundExternalSamplingMCCFR
from m5q_support_range_feasibility import (
    exact_terminal_utility_range,
    external_sampling_support_report,
)
from m5q_variance_mstar_floor import appendix_c_mstar_zero_variance_floor

SCHEMA = "openofc-m5q-support-range-feasibility-pilot-v1"
AUTHORITY = "EXTERNAL_SAMPLING_SUPPORT_RANGE_PILOT_NOT_CERTIFICATION"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "m5q_support_range_feasibility.json"
TARGET = 0.15
PROBE_ITERATIONS = 1_000_000
MCCFR_SEED = 2026090201
CHECKPOINTS = (0, 1, 4, 16)


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _source_manifest() -> dict[str, object]:
    paths = (
        "deepofc/hu_two_round.py",
        "deepofc/hu_two_round_br.py",
        "deepofc/hu_two_round_hidden_discard.py",
        "deepofc/hu_two_round_joker.py",
        "deepofc/hu_two_round_mccfr.py",
        "tools/openofc_solver/M5Q_SUPPORT_RANGE_FEASIBILITY_CONTRACT.md",
        "tools/openofc_solver/m5q_support_range_feasibility.py",
        "tools/openofc_solver/m5q_variance_mstar_floor.py",
        "tools/openofc_solver/run_m5q_support_range_feasibility.py",
        "tools/openofc_solver/test_m5q_support_range_feasibility.py",
    )
    rows = [
        {"path": rel, "sha256": hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()}
        for rel in paths
    ]
    payload: dict[str, object] = {"files": rows}
    payload["sha256"] = _sha(payload)
    return payload


def _range_row(family_id: str, game) -> dict[str, object]:
    exact_range = exact_terminal_utility_range(game)
    floor = appendix_c_mstar_zero_variance_floor(
        game,
        game.uniform_profile(),
        utility_range=exact_range.utility_range,
        sampling_probability_floor=1.0,
    )
    return {
        "family_id": family_id,
        "exact_terminal_utility_range": exact_range.payload(),
        "appendix_c_impossible_best_case": {
            "variance_assumption": 0.0,
            "sampling_probability_floor_assumption": 1.0,
            "floor": floor.payload(),
            "bound_at_probe_iterations": floor.bound_at(PROBE_ITERATIONS),
            "required_iterations_for_target": floor.required_iterations(TARGET),
        },
    }


def main() -> None:
    joker = HUTwoRoundJokerSubgame()
    hidden = HUTwoRoundHiddenDiscardSubgame()

    ranges = [
        _range_row("joker", joker),
        _range_row("hidden-discard", hidden),
    ]

    solver = TwoRoundExternalSamplingMCCFR(joker, seed=MCCFR_SEED)
    support_rows: list[dict[str, object]] = []
    previous = 0
    for checkpoint in CHECKPOINTS:
        if checkpoint < previous:
            raise ValueError("M5Q support checkpoints must be nondecreasing")
        solver.run(checkpoint - previous)
        report = external_sampling_support_report(
            joker,
            solver.current_profile(),
            profile_id=f"external-sampling-current-{checkpoint}",
        )
        support_rows.append(
            {
                "checkpoint": checkpoint,
                "solver_iteration": solver.iteration,
                "support": report.payload(),
            }
        )
        previous = checkpoint

    post_update = [row for row in support_rows if int(row["checkpoint"]) > 0]
    zero_checkpoints = [
        int(row["checkpoint"])
        for row in post_update
        if (
            int(row["support"]["player0_traverser"]["zero_probability_histories"]) > 0
            or int(row["support"]["player1_traverser"]["zero_probability_histories"]) > 0
        )
    ]
    exact_range_map = {
        str(row["family_id"]): float(row["exact_terminal_utility_range"]["utility_range"])
        for row in ranges
    }
    required_map = {
        str(row["family_id"]): int(
            row["appendix_c_impossible_best_case"]["required_iterations_for_target"]
        )
        for row in ranges
    }

    payload: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "target_exploitability": TARGET,
        "probe_iterations": PROBE_ITERATIONS,
        "mccfr_seed": MCCFR_SEED,
        "checkpoints": list(CHECKPOINTS),
        "source_manifest": _source_manifest(),
        "range_rows": ranges,
        "support_rows": support_rows,
        "summary": {
            "exact_terminal_utility_ranges": exact_range_map,
            "appendix_c_delta1_var0_required_iterations": required_map,
            "post_update_zero_sampling_support_detected": bool(zero_checkpoints),
            "zero_support_checkpoints": zero_checkpoints,
            "actual_estimator_variance_measured": False,
            "production_certification_eligible": False,
            "real_routes_certified": 0,
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
