from __future__ import annotations

"""Run the frozen M5Q explicit-exploration support feasibility pilot."""

import hashlib
import json
from pathlib import Path

from deepofc.hu_two_round_hidden_discard import HUTwoRoundHiddenDiscardSubgame
from deepofc.hu_two_round_joker import HUTwoRoundJokerSubgame
from m5q_exploration_support_feasibility import exploration_structural_support_report
from m5q_support_range_feasibility import exact_terminal_utility_range
from m5q_variance_mstar_floor import appendix_c_mstar_zero_variance_floor

SCHEMA = "openofc-m5q-exploration-support-feasibility-pilot-v1"
AUTHORITY = "EXPLORATION_SUPPORTED_EXTERNAL_SAMPLING_PILOT_NOT_CERTIFICATION"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "m5q_exploration_support_feasibility.json"
TARGET = 0.15
EPSILONS = (0.01, 0.05, 0.10, 0.20, 1.00)


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
        "tools/openofc_solver/M5Q_EXPLORATION_SUPPORT_FEASIBILITY_CONTRACT.md",
        "tools/openofc_solver/m5q_exploration_support_feasibility.py",
        "tools/openofc_solver/m5q_support_range_feasibility.py",
        "tools/openofc_solver/m5q_variance_mstar_floor.py",
        "tools/openofc_solver/run_m5q_exploration_support_feasibility.py",
        "tools/openofc_solver/test_m5q_exploration_support_feasibility.py",
    )
    rows = [
        {"path": rel, "sha256": hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()}
        for rel in paths
    ]
    payload: dict[str, object] = {"files": rows}
    payload["sha256"] = _sha(payload)
    return payload


def _family_row(family_id: str, game) -> dict[str, object]:
    exact_range = exact_terminal_utility_range(game)
    rows: list[dict[str, object]] = []
    for epsilon in EPSILONS:
        support = exploration_structural_support_report(game, epsilon)
        floor = appendix_c_mstar_zero_variance_floor(
            game,
            game.uniform_profile(),
            utility_range=exact_range.utility_range,
            sampling_probability_floor=support.global_sampling_probability_floor,
        )
        rows.append(
            {
                "epsilon": epsilon,
                "support": support.payload(),
                "appendix_c_zero_variance_uniform_profile": {
                    "floor": floor.payload(),
                    "required_iterations_for_target": floor.required_iterations(TARGET),
                },
            }
        )
    best = next(row for row in rows if float(row["epsilon"]) == 1.0)
    return {
        "family_id": family_id,
        "exact_terminal_utility_range": exact_range.payload(),
        "epsilon_rows": rows,
        "best_guaranteed_support_endpoint": {
            "epsilon": 1.0,
            "global_sampling_probability_floor": best["support"][
                "global_sampling_probability_floor"
            ],
            "required_iterations_for_target": best[
                "appendix_c_zero_variance_uniform_profile"
            ]["required_iterations_for_target"],
        },
    }


def main() -> None:
    families = [
        _family_row("joker", HUTwoRoundJokerSubgame()),
        _family_row("hidden-discard", HUTwoRoundHiddenDiscardSubgame()),
    ]
    best_required = {
        str(row["family_id"]): int(
            row["best_guaranteed_support_endpoint"]["required_iterations_for_target"]
        )
        for row in families
    }
    best_delta = {
        str(row["family_id"]): float(
            row["best_guaranteed_support_endpoint"][
                "global_sampling_probability_floor"
            ]
        )
        for row in families
    }
    payload: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "target_exploitability": TARGET,
        "epsilon_ladder": list(EPSILONS),
        "source_manifest": _source_manifest(),
        "families": families,
        "summary": {
            "strictly_positive_support_restored_for_all_epsilon_rows": all(
                float(row["support"]["global_sampling_probability_floor"]) > 0.0
                for family in families
                for row in family["epsilon_rows"]
            ),
            "epsilon1_is_best_guaranteed_support_endpoint": True,
            "epsilon1_global_sampling_probability_floor": best_delta,
            "epsilon1_required_iterations_for_target": best_required,
            "actual_training_semantics_changed": False,
            "actual_convergence_quality_measured": False,
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
