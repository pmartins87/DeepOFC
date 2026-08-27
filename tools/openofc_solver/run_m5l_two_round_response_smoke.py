from __future__ import annotations

"""Mechanics-only exact-BR smoke for the M5L two-round response learner.

This intentionally uses the base two-round benchmark, which is excluded from Q2
held-out families.  Its sole purpose is to verify that the new fixed-opponent
response learner, pure-response materialization and independent exact replay obey
`approximate_response <= exact_best_response` for both persistent players.
"""

from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from deepofc.hu_two_round import HUTwoRoundSubgame
from deepofc.hu_two_round_br import exact_best_response, profile_with_pure_response
from m5l_two_round_response import TwoRoundOutcomeSampledResponseLearner

SCHEMA = "openofc-m5l-two-round-response-smoke-v1"
AUTHORITY = "TWO_ROUND_RESPONSE_MECHANICS_SMOKE_NOT_Q2_NOT_CERTIFICATION"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "m5l_two_round_response_smoke.json"
BUDGET = 256
EPSILON = 0.6
BASE_SEED = 2026083051
TOL = 1e-9


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _exact_replay(game, profile, player, exact) -> float:
    merged = profile_with_pure_response(game, profile, exact)
    u0 = float(game.expected_u0(merged))
    return u0 if player == 0 else -u0


def main() -> None:
    game = HUTwoRoundSubgame()
    profile = {}
    rows: list[dict[str, object]] = []
    for player in (0, 1):
        exact = exact_best_response(game, profile, player)
        exact_replay = _exact_replay(game, profile, player, exact)
        if abs(float(exact.value) - exact_replay) > 1e-10:
            raise RuntimeError("M5L two-round exact BR replay mismatch")
        learner = TwoRoundOutcomeSampledResponseLearner(
            game,
            profile,
            deviator_player=player,
            epsilon=EPSILON,
            seed=BASE_SEED + player,
        )
        training = learner.run_to(BUDGET)
        pure, learned, fallback = learner.pure_response(exact)
        approximate = learner.exact_value_of_pure_response(pure)
        residual = float(exact.value - approximate)
        if residual < -TOL:
            raise RuntimeError("M5L two-round learned response exceeded exact BR")
        total = len(exact.choices)
        rows.append(
            {
                "player": player,
                "exact_best_response_value": float(exact.value),
                "exact_replay_value": exact_replay,
                "approximate_response_value": approximate,
                "underestimation_residual": max(0.0, residual),
                "responding_infosets": total,
                "responding_infosets_learned": learned,
                "responding_infosets_fallback": fallback,
                "responding_infoset_coverage": learned / total if total else 1.0,
                "training": asdict(training),
            }
        )

    payload: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "benchmark": "BASE_TWO_ROUND_MECHANICS_ONLY_EXCLUDED_FROM_Q2_HELDOUT",
        "budget": BUDGET,
        "epsilon": EPSILON,
        "rows": rows,
        "summary": {
            "players": [0, 1],
            "rows": len(rows),
            "max_underestimation_residual": max(float(row["underestimation_residual"]) for row in rows),
            "certification_eligible": False,
            "q2_evidence": False,
        },
    }
    payload["sha256"] = _sha(payload)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"artifact": str(OUT.relative_to(ROOT)), "sha256": payload["sha256"], "summary": payload["summary"]}, sort_keys=True))


if __name__ == "__main__":
    main()
