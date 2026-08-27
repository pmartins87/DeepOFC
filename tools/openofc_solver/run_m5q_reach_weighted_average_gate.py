from __future__ import annotations

"""Run the frozen M5Q reach-weighted average semantic-equivalence gate."""

from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from deepofc.hu_two_round_cfr import TwoRoundFullTreeCFR
from deepofc.hu_two_round_hidden_discard import HUTwoRoundHiddenDiscardSubgame
from deepofc.hu_two_round_joker import HUTwoRoundJokerSubgame
from deepofc.hu_two_round_mccfr import TwoRoundExternalSamplingMCCFR
from m5q_external_sampling_unbiasedness import frozen_regret_table
from m5q_reach_weighted_mccfr_average import (
    AUTHORITY as AVERAGE_AUTHORITY,
    ReachWeightedAverageExternalSamplingMCCFR,
)

SCHEMA = "openofc-m5q-reach-weighted-average-gate-v1"
AUTHORITY = "REACH_WEIGHTED_AVERAGE_SEMANTIC_GATE_NOT_CERTIFICATION"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "m5q_reach_weighted_average_gate.json"
TOLERANCE = 1e-15
TRAINING_INVARIANCE_STEPS = 3
TRAINING_INVARIANCE_SEED = 2026090411
AVERAGE_DISTINCTION_STEPS = 4
AVERAGE_DISTINCTION_SEED = 2026090429


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _copy(table):
    return {
        info: {action: float(value) for action, value in values.items()}
        for info, values in table.items()
    }


def _max_profile_difference(a, b) -> float:
    worst = 0.0
    for info in a:
        for action in a[info]:
            worst = max(worst, abs(float(a[info][action]) - float(b[info][action])))
    return worst


def _max_regret_difference(a, b) -> float:
    worst = 0.0
    for info in a:
        for action in a[info]:
            worst = max(worst, abs(float(a[info][action]) - float(b[info][action])))
    return worst


def _family_equivalence(family_id: str, game) -> dict[str, object]:
    frozen = frozen_regret_table(game, "hash-mixed")
    reference = TwoRoundFullTreeCFR(game, variant="cfr")
    reference.regrets = _copy(frozen)
    candidate = ReachWeightedAverageExternalSamplingMCCFR(game, seed=73)
    candidate.regrets = _copy(frozen)

    reference.step()
    candidate.step()

    difference = _max_profile_difference(
        reference.average_profile(), candidate.reach_weighted_average_profile()
    )
    return {
        "family_id": family_id,
        "frozen_profile_rule": "hash-mixed",
        "max_action_probability_difference": difference,
        "tolerance": TOLERANCE,
        "passes": difference <= TOLERANCE,
        "candidate_recorded_iterations": candidate.reach_weighted_recorded_iterations,
        "candidate_average_authority": candidate.average_authority,
    }


def _training_invariance() -> dict[str, object]:
    game = HUTwoRoundJokerSubgame()
    plain = TwoRoundExternalSamplingMCCFR(game, seed=TRAINING_INVARIANCE_SEED)
    candidate = ReachWeightedAverageExternalSamplingMCCFR(
        game, seed=TRAINING_INVARIANCE_SEED
    )
    plain.run(TRAINING_INVARIANCE_STEPS)
    candidate.run(TRAINING_INVARIANCE_STEPS)
    regret_difference = _max_regret_difference(plain.regrets, candidate.regrets)
    rng_identical = plain.rng.getstate() == candidate.rng.getstate()
    return {
        "family_id": "joker",
        "steps": TRAINING_INVARIANCE_STEPS,
        "seed": TRAINING_INVARIANCE_SEED,
        "max_regret_difference": regret_difference,
        "rng_state_identical": rng_identical,
        "passes": regret_difference == 0.0 and rng_identical,
    }


def _average_distinction() -> dict[str, object]:
    game = HUTwoRoundJokerSubgame()
    candidate = ReachWeightedAverageExternalSamplingMCCFR(
        game, seed=AVERAGE_DISTINCTION_SEED
    )
    candidate.run(AVERAGE_DISTINCTION_STEPS)
    difference = _max_profile_difference(
        candidate.reach_weighted_average_profile(),
        candidate.behavioral_time_average_profile(),
    )
    return {
        "family_id": "joker",
        "steps": AVERAGE_DISTINCTION_STEPS,
        "seed": AVERAGE_DISTINCTION_SEED,
        "max_difference_vs_local_behavioral_time_average": difference,
        "passes": difference > 0.0,
        "status": asdict(candidate.reach_weighted_average_status()),
    }


def _source_manifest() -> dict[str, object]:
    paths = (
        "deepofc/hu_two_round_cfr.py",
        "deepofc/hu_two_round_mccfr.py",
        "tools/openofc_solver/M5Q_REACH_WEIGHTED_AVERAGE_GATE_CONTRACT.md",
        "tools/openofc_solver/m5q_reach_weighted_mccfr_average.py",
        "tools/openofc_solver/test_m5q_reach_weighted_mccfr_average.py",
        "tools/openofc_solver/run_m5q_reach_weighted_average_gate.py",
    )
    rows = [
        {"path": rel, "sha256": hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()}
        for rel in paths
    ]
    payload: dict[str, object] = {"files": rows}
    payload["sha256"] = _sha(payload)
    return payload


def main() -> None:
    families = [
        _family_equivalence("joker", HUTwoRoundJokerSubgame()),
        _family_equivalence("hidden-discard", HUTwoRoundHiddenDiscardSubgame()),
    ]
    invariance = _training_invariance()
    distinction = _average_distinction()
    semantic_pass = all(bool(row["passes"]) for row in families)
    gate_pass = semantic_pass and bool(invariance["passes"]) and bool(distinction["passes"])

    payload: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "candidate_average_authority": AVERAGE_AUTHORITY,
        "source_manifest": _source_manifest(),
        "family_equivalence": families,
        "sampled_training_invariance": invariance,
        "legacy_average_distinction": distinction,
        "summary": {
            "reduced_game_reach_weighted_average_semantics_validated": semantic_pass,
            "sampled_regret_training_semantics_unchanged": bool(invariance["passes"]),
            "candidate_distinct_from_local_behavioral_time_average": bool(distinction["passes"]),
            "gate_pass": gate_pass,
            "full_game_scalable_average_implementation_validated": False,
            "predictable_variance_accounting_available": False,
            "next_blocker": "PREDICTABLE_VARIANCE_ACCOUNTING_MISSING" if gate_pass else "REACH_WEIGHTED_AVERAGE_GATE_FAILED",
            "production_certification_eligible": False,
            "real_routes_certified": 0,
        },
    }
    payload["sha256"] = _sha(payload)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"artifact": str(OUT.relative_to(ROOT)), "sha256": payload["sha256"], "summary": payload["summary"]}, sort_keys=True))
    if not gate_pass:
        raise SystemExit("M5Q reach-weighted average semantic gate failed")


if __name__ == "__main__":
    main()
