from __future__ import annotations

"""Run the frozen M5Q coordinate-wise Freedman feasibility screen."""

import hashlib
import json
from pathlib import Path

from deepofc.hu_two_round_hidden_discard import HUTwoRoundHiddenDiscardSubgame
from deepofc.hu_two_round_joker import HUTwoRoundJokerSubgame
from m5q_freedman_union_feasibility import evaluate_family, report_payload

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "m5q_freedman_union_feasibility.json"
TARGET_EXPLOITABILITY = 0.15
FAMILYWISE_FAILURE_PROBABILITY = 0.05
PROBE_ITERATIONS = 1_000_000


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _source_manifest() -> dict[str, object]:
    paths = (
        "deepofc/hu_two_round.py",
        "deepofc/hu_two_round_hidden_discard.py",
        "deepofc/hu_two_round_joker.py",
        "tools/openofc_solver/M5Q_FREEDMAN_UNION_FEASIBILITY_CONTRACT.md",
        "tools/openofc_solver/m5q_freedman_union_feasibility.py",
        "tools/openofc_solver/m5q_support_range_feasibility.py",
        "tools/openofc_solver/run_m5q_freedman_union_feasibility.py",
        "tools/openofc_solver/test_m5q_freedman_union_feasibility.py",
    )
    rows = [
        {"path": rel, "sha256": hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()}
        for rel in paths
    ]
    payload: dict[str, object] = {"files": rows}
    payload["sha256"] = _sha(payload)
    return payload


def main() -> None:
    results = (
        evaluate_family(
            "joker",
            HUTwoRoundJokerSubgame(),
            target_exploitability=TARGET_EXPLOITABILITY,
            familywise_failure_probability=FAMILYWISE_FAILURE_PROBABILITY,
            probe_iterations=PROBE_ITERATIONS,
        ),
        evaluate_family(
            "hidden-discard",
            HUTwoRoundHiddenDiscardSubgame(),
            target_exploitability=TARGET_EXPLOITABILITY,
            familywise_failure_probability=FAMILYWISE_FAILURE_PROBABILITY,
            probe_iterations=PROBE_ITERATIONS,
        ),
    )
    report = report_payload(results)
    required = {
        row.structure.family_id: row.required_iterations_for_target_concentration_only
        for row in results
    }
    concentration_at_probe = {
        row.structure.family_id: row.concentration_only_exploitability_at_probe
        for row in results
    }
    coordinate_counts = {
        row.structure.family_id: row.structure.action_coordinates
        for row in results
    }

    payload: dict[str, object] = {
        "target_exploitability": TARGET_EXPLOITABILITY,
        "familywise_failure_probability": FAMILYWISE_FAILURE_PROBABILITY,
        "probe_iterations": PROBE_ITERATIONS,
        "report": report,
        "source_manifest": _source_manifest(),
        "summary": {
            "action_coordinates": coordinate_counts,
            "concentration_only_exploitability_at_probe": concentration_at_probe,
            "required_iterations_for_target_concentration_only": required,
            "sampled_positive_regret_term_assumed_zero": True,
            "actual_predictable_variance_measured": False,
            "worst_case_variance_envelope_only": True,
            "coordinate_union_architecture_fully_evaluated": True,
            "production_certification_eligible": False,
            "real_routes_certified": 0,
        },
    }
    payload["sha256"] = _sha(payload)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"artifact": str(OUT.relative_to(ROOT)), "sha256": payload["sha256"], "summary": payload["summary"]}, sort_keys=True))


if __name__ == "__main__":
    main()
