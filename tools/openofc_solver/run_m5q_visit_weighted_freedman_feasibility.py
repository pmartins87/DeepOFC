from __future__ import annotations

"""Run the frozen M5Q visit-weighted Freedman feasibility screen."""

from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from deepofc.hu_two_round_hidden_discard import HUTwoRoundHiddenDiscardSubgame
from deepofc.hu_two_round_joker import HUTwoRoundJokerSubgame
from deepofc.hu_two_round_mccfr import TwoRoundExternalSamplingMCCFR
from m5q_external_sampling_unbiasedness import frozen_regret_table
from m5q_visit_weighted_freedman_feasibility import evaluate_profile

SCHEMA = "openofc-m5q-visit-weighted-freedman-feasibility-pilot-v1"
AUTHORITY = "VISIT_WEIGHTED_FREEDMAN_FEASIBILITY_PILOT_NOT_CERTIFICATION"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "m5q_visit_weighted_freedman_feasibility.json"
TARGET = 0.15
ALPHA = 0.05
PROBE_ITERATIONS = 1_000_000
PROFILE_RULES = ("uniform", "hash-mixed")
PREDICTABLE_EVIDENCE = ROOT / "evidence" / "strategic" / "m5q_predictable_visit_variance_2026-08-27.json"
COARSE_EVIDENCE = ROOT / "evidence" / "strategic" / "m5q_freedman_union_feasibility_2026-08-27.json"
EXPECTED_PREDICTABLE_PAYLOAD_SHA = "bd0312c66eb13151a7159f1e42eafbba72544b7ab1ad272bf867cba27ce13f51"
EXPECTED_COARSE_PAYLOAD_SHA = "2a38e5415cd68ae8fa5bbf213b3944273c7291e635a622612ab642e17eb7c01e"


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _load_bound_evidence() -> tuple[dict[str, float], dict[str, int]]:
    predictable = json.loads(PREDICTABLE_EVIDENCE.read_text(encoding="utf-8"))
    coarse = json.loads(COARSE_EVIDENCE.read_text(encoding="utf-8"))
    if predictable.get("sha256") != EXPECTED_PREDICTABLE_PAYLOAD_SHA:
        raise RuntimeError("predictable visit-variance evidence identity mismatch")
    if coarse.get("sha256") != EXPECTED_COARSE_PAYLOAD_SHA:
        raise RuntimeError("coarse Freedman evidence identity mismatch")
    ranges: dict[str, float] = {}
    for row in predictable["rows"]:
        family = str(row["family_id"])
        delta = float(row["exact_terminal_utility_range"]["utility_range"])
        old = ranges.setdefault(family, delta)
        if old != delta:
            raise AssertionError("predictable evidence utility-range mismatch across profiles")
    required = {
        str(family): int(value)
        for family, value in coarse["summary"]["required_iterations_for_target_concentration_only"].items()
    }
    return ranges, required


def _profile(game, rule: str):
    if rule == "uniform":
        return game.uniform_profile()
    solver = TwoRoundExternalSamplingMCCFR(game, seed=1)
    solver.regrets = frozen_regret_table(game, rule)
    return solver.current_profile()


def _source_manifest() -> dict[str, object]:
    paths = (
        "deepofc/hu_two_round_mccfr.py",
        "evidence/strategic/m5q_freedman_union_feasibility_2026-08-27.json",
        "evidence/strategic/m5q_predictable_visit_variance_2026-08-27.json",
        "tools/openofc_solver/M5Q_VISIT_WEIGHTED_FREEDMAN_FEASIBILITY_CONTRACT.md",
        "tools/openofc_solver/m5q_predictable_visit_variance.py",
        "tools/openofc_solver/m5q_visit_weighted_freedman_feasibility.py",
        "tools/openofc_solver/run_m5q_visit_weighted_freedman_feasibility.py",
        "tools/openofc_solver/test_m5q_visit_weighted_freedman_feasibility.py",
    )
    rows = [
        {"path": rel, "sha256": hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()}
        for rel in paths
    ]
    payload: dict[str, object] = {"files": rows}
    payload["sha256"] = _sha(payload)
    return payload


def main() -> None:
    utility_ranges, coarse_required = _load_bound_evidence()
    families = (
        ("joker", HUTwoRoundJokerSubgame()),
        ("hidden-discard", HUTwoRoundHiddenDiscardSubgame()),
    )
    rows: list[dict[str, object]] = []
    for family_id, game in families:
        delta = utility_ranges[family_id]
        for rule in PROFILE_RULES:
            result = evaluate_profile(
                family_id,
                rule,
                game,
                _profile(game, rule),
                utility_range=delta,
                familywise_failure_probability=ALPHA,
                target_exploitability=TARGET,
                probe_iterations=PROBE_ITERATIONS,
            )
            row = asdict(result)
            row["coarse_required_iterations"] = coarse_required[family_id]
            row["required_iteration_improvement_factor_vs_coarse"] = (
                float(coarse_required[family_id])
                / float(result.required_iterations_for_target_concentration_only)
            )
            rows.append(row)

    required = {
        f"{row['family_id']}:{row['profile_id']}": row["required_iterations_for_target_concentration_only"]
        for row in rows
    }
    improvements = {
        f"{row['family_id']}:{row['profile_id']}": row["required_iteration_improvement_factor_vs_coarse"]
        for row in rows
    }
    payload: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "target_exploitability": TARGET,
        "familywise_failure_probability": ALPHA,
        "probe_iterations": PROBE_ITERATIONS,
        "profile_rules": list(PROFILE_RULES),
        "predictable_evidence_payload_sha256": EXPECTED_PREDICTABLE_PAYLOAD_SHA,
        "coarse_freedman_payload_sha256": EXPECTED_COARSE_PAYLOAD_SHA,
        "source_manifest": _source_manifest(),
        "rows": rows,
        "summary": {
            "required_iterations_for_target_concentration_only": required,
            "improvement_factor_vs_coarse_freedman": improvements,
            "sampled_positive_regret_term_assumed_zero": True,
            "frozen_profile_extrapolation_only": True,
            "adaptive_training_trajectory_certified": False,
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
