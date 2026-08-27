from __future__ import annotations

"""Run the frozen adaptive predictable-Freedman Joker trajectory pilot."""

from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from deepofc.hu_two_round_joker import HUTwoRoundJokerSubgame
from deepofc.hu_two_round_mccfr import TwoRoundExternalSamplingMCCFR
from m5q_predictable_freedman_trajectory import PredictableVarianceExternalSamplingMCCFR

SCHEMA = "openofc-m5q-predictable-freedman-trajectory-pilot-v1"
AUTHORITY = "ADAPTIVE_PREDICTABLE_FREEDMAN_TRAJECTORY_PILOT_NOT_CERTIFICATION"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "m5q_predictable_freedman_trajectory.json"
SEED = 2026090601
CHECKPOINTS = (1, 4, 16, 64)
ALPHA = 0.05
UTILITY_RANGE = 4.0
PREDICTABLE_EVIDENCE_SHA = "bd0312c66eb13151a7159f1e42eafbba72544b7ab1ad272bf867cba27ce13f51"


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _max_regret_difference(a, b) -> float:
    worst = 0.0
    for info in a:
        for action in a[info]:
            worst = max(worst, abs(float(a[info][action]) - float(b[info][action])))
    return worst


def _source_manifest() -> dict[str, object]:
    paths = (
        "deepofc/hu_two_round_mccfr.py",
        "evidence/strategic/m5q_predictable_visit_variance_2026-08-27.json",
        "tools/openofc_solver/M5Q_PREDICTABLE_FREEDMAN_TRAJECTORY_CONTRACT.md",
        "tools/openofc_solver/m5q_predictable_visit_variance.py",
        "tools/openofc_solver/m5q_predictable_freedman_trajectory.py",
        "tools/openofc_solver/run_m5q_predictable_freedman_trajectory.py",
        "tools/openofc_solver/test_m5q_predictable_freedman_trajectory.py",
    )
    rows = [
        {"path": rel, "sha256": hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()}
        for rel in paths
    ]
    payload: dict[str, object] = {"files": rows}
    payload["sha256"] = _sha(payload)
    return payload


def main() -> None:
    predictable_evidence = json.loads(
        (ROOT / "evidence" / "strategic" / "m5q_predictable_visit_variance_2026-08-27.json").read_text(encoding="utf-8")
    )
    if predictable_evidence.get("sha256") != PREDICTABLE_EVIDENCE_SHA:
        raise RuntimeError("predictable visit-variance evidence identity mismatch")

    game = HUTwoRoundJokerSubgame()
    solver = PredictableVarianceExternalSamplingMCCFR(game, seed=SEED)
    rows: list[dict[str, object]] = []
    previous = 0
    for checkpoint in CHECKPOINTS:
        solver.run(checkpoint - previous)
        bound = solver.regret_bound(
            utility_range=UTILITY_RANGE,
            familywise_failure_probability=ALPHA,
        )
        rows.append({"checkpoint": checkpoint, "bound": asdict(bound)})
        previous = checkpoint

    plain = TwoRoundExternalSamplingMCCFR(game, seed=SEED)
    plain.run(CHECKPOINTS[-1])
    invariance = {
        "iterations": CHECKPOINTS[-1],
        "max_regret_difference": _max_regret_difference(plain.regrets, solver.regrets),
        "rng_state_identical": plain.rng.getstate() == solver.rng.getstate(),
        "predictable_accounted_iterations": solver.predictable_accounted_iterations,
    }
    invariance["passes"] = (
        invariance["max_regret_difference"] == 0.0
        and invariance["rng_state_identical"] is True
        and invariance["predictable_accounted_iterations"] == CHECKPOINTS[-1]
    )

    payload: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "family_id": "joker",
        "seed": SEED,
        "checkpoints": list(CHECKPOINTS),
        "familywise_failure_probability": ALPHA,
        "utility_range": UTILITY_RANGE,
        "predictable_visit_evidence_sha256": PREDICTABLE_EVIDENCE_SHA,
        "source_manifest": _source_manifest(),
        "rows": rows,
        "training_invariance": invariance,
        "summary": {
            "final_checkpoint": CHECKPOINTS[-1],
            "final_sampled_positive_regret_exploitability": rows[-1]["bound"]["sampled_positive_regret_exploitability"],
            "final_concentration_additive_exploitability": rows[-1]["bound"]["concentration_additive_exploitability"],
            "final_freedman_exploitability_upper": rows[-1]["bound"]["exploitability_upper"],
            "training_semantics_unchanged": bool(invariance["passes"]),
            "adaptive_predictable_variance_accumulated": True,
            "formal_unbiasedness_proof_bound_to_implementation": False,
            "full_game_scalable_average_validated": False,
            "production_certification_eligible": False,
            "real_routes_certified": 0,
        },
    }
    payload["sha256"] = _sha(payload)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"artifact": str(OUT.relative_to(ROOT)), "sha256": payload["sha256"], "summary": payload["summary"]}, sort_keys=True))
    if not invariance["passes"]:
        raise SystemExit("M5Q predictable-Freedman instrumentation changed training trajectory")


if __name__ == "__main__":
    main()
