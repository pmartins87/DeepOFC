from __future__ import annotations

"""M5L Q0B: extend the uniform-profile response budget ladder.

Q0 established pipeline correctness and showed substantial exact-vs-learned BR
residual at 1024 response episodes.  Q0B keeps the same game, profile, epsilon
and training seeds, but continues each learner cumulatively to larger budgets so
we can distinguish a mere scale problem from a structural generalization problem.

This remains calibration-only and cannot create certification authority.
"""

import hashlib
import json
import math
from pathlib import Path

from deepofc.hu_three_round_br import exact_best_response, exact_value_of_pure_response
from deepofc.hu_three_round_sequential import HUThreeRoundSequentialSubgame, StrategyProfile
from tools.openofc_solver.run_m5l_three_round_q0 import (
    BASE_SEED,
    EPSILON,
    OutcomeSampledResponseLearner,
    _seed64,
)

SCHEMA = "openofc-m5l-three-round-q0b-scale-v1"
AUTHORITY = "QUALIFICATION_SCALE_DIAGNOSTIC_NOT_CERTIFICATION"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "m5l_three_round_q0b_scale.json"
BUDGETS = (1024, 4096, 16384, 65536)
TOL = 1e-9


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _source_manifest() -> dict[str, object]:
    paths = (
        "deepofc/hu_three_round_br.py",
        "deepofc/hu_three_round_sequential.py",
        "tools/openofc_solver/M5L_REFERENCE_EVALUATOR_QUALIFICATION_CONTRACT.md",
        "tools/openofc_solver/run_m5l_three_round_q0.py",
        "tools/openofc_solver/run_m5l_three_round_q0b_scale.py",
    )
    rows = [
        {"path": rel, "sha256": hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()}
        for rel in paths
    ]
    payload: dict[str, object] = {"files": rows}
    payload["sha256"] = _sha(payload)
    return payload


def main() -> None:
    game = HUThreeRoundSequentialSubgame()
    opponent_profile: StrategyProfile = {}
    rows: list[dict[str, object]] = []

    for player in (0, 1):
        exact = exact_best_response(game, opponent_profile, player)
        exact_replay, exact_replay_terminals = exact_value_of_pure_response(
            game, opponent_profile, exact
        )
        if abs(float(exact.value) - float(exact_replay)) > 1e-10:
            raise RuntimeError("M5L Q0B exact BR independent replay mismatch")

        learner = OutcomeSampledResponseLearner(
            game,
            opponent_profile,
            deviator_player=player,
            epsilon=EPSILON,
            seed=_seed64(BASE_SEED, "q0", player),
        )
        for budget in BUDGETS:
            learner.run_to(budget)
            pure, learned_infosets, fallback_infosets = learner.pure_response(exact)
            approximate_value, approximate_replay_terminals = exact_value_of_pure_response(
                game, opponent_profile, pure
            )
            residual = float(exact.value - approximate_value)
            if residual < -TOL:
                raise RuntimeError("M5L Q0B approximate response exceeded exact BR")
            total_infosets = len(exact.choices)
            rows.append(
                {
                    "player": player,
                    "budget": budget,
                    "training_seed": learner.seed,
                    "exact_best_response_value": float(exact.value),
                    "exact_replay_value": float(exact_replay),
                    "exact_best_response_infosets": total_infosets,
                    "exact_best_response_terminal_histories": int(exact.terminal_histories),
                    "exact_replay_terminals": int(exact_replay_terminals),
                    "approximate_response_value": float(approximate_value),
                    "approximate_replay_terminals": int(approximate_replay_terminals),
                    "underestimation_residual": max(0.0, residual),
                    "responding_infosets_learned": int(learned_infosets),
                    "responding_infosets_fallback": int(fallback_infosets),
                    "responding_infoset_coverage": (
                        float(learned_infosets) / float(total_infosets)
                        if total_infosets else 1.0
                    ),
                    "learner_terminal_evaluations": int(learner.terminal_evaluations),
                }
            )

    if any(not math.isfinite(float(row["underestimation_residual"])) for row in rows):
        raise RuntimeError("M5L Q0B produced non-finite residual")

    by_player: dict[str, list[dict[str, object]]] = {}
    for player in (0, 1):
        by_player[str(player)] = [row for row in rows if row["player"] == player]

    payload: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "qualification_stage": "Q0B_RESPONSE_SCALE_DIAGNOSTIC",
        "candidate_profile": "UNIFORM",
        "budgets": list(BUDGETS),
        "epsilon": EPSILON,
        "base_seed": BASE_SEED,
        "source_manifest": _source_manifest(),
        "rows": rows,
        "summary": {
            "rows": len(rows),
            "players": [0, 1],
            "max_underestimation_residual": max(float(row["underestimation_residual"]) for row in rows),
            "min_underestimation_residual": min(float(row["underestimation_residual"]) for row in rows),
            "max_infoset_coverage": max(float(row["responding_infoset_coverage"]) for row in rows),
            "per_player_final": {
                player: {
                    "budget": int(items[-1]["budget"]),
                    "underestimation_residual": float(items[-1]["underestimation_residual"]),
                    "responding_infoset_coverage": float(items[-1]["responding_infoset_coverage"]),
                    "approximate_response_value": float(items[-1]["approximate_response_value"]),
                }
                for player, items in by_player.items()
            },
            "certification_eligible": False,
            "reference_manifest_emitted": False,
        },
    }
    payload["sha256"] = _sha(payload)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"artifact": str(OUT.relative_to(ROOT)), "sha256": payload["sha256"], "summary": payload["summary"]}, sort_keys=True))


if __name__ == "__main__":
    main()
