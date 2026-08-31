from __future__ import annotations

"""Run one M5R conservative three-round BR interval validation cell."""

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools/openofc_solver"
for candidate in (ROOT, TOOLS):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from deepofc.hu_three_round_br import exact_best_response
from deepofc.hu_three_round_sequential import HUThreeRoundSequentialSubgame
from deepofc.hu_three_round_sequential_v2 import HUThreeRoundSequentialSubgameV2
from m5r_three_round_interval_bridge import conservative_three_round_br_interval

AUTHORITY = "M5R_THREE_ROUND_INTERVAL_BRIDGE_VALIDATION_ONLY_NOT_ROUTE_CERTIFICATION"
SCHEMA = "openofc-m5r-three-round-interval-bridge-cell-v1"
THRESHOLDS = (0.0, 0.01, 0.05)
TOLERANCE = 1e-10


def _case(family: str):
    if family == "three-round-v1":
        return HUThreeRoundSequentialSubgame(), 1_312_200
    if family == "three-round-v2":
        return HUThreeRoundSequentialSubgameV2(), 839_808
    raise ValueError(f"unsupported family {family}")


def _sha(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", choices=("three-round-v1", "three-round-v2"), required=True)
    ap.add_argument("--player", type=int, choices=(0, 1), required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    game, expected_terminals = _case(args.family)
    profile = {}

    started = time.perf_counter()
    exact = exact_best_response(game, profile, args.player)
    exact_seconds = time.perf_counter() - started
    if exact.terminal_histories != expected_terminals:
        raise SystemExit(
            f"exact reference work drift: {exact.terminal_histories} != {expected_terminals}"
        )

    rows = []
    for threshold in THRESHOLDS:
        started = time.perf_counter()
        result = conservative_three_round_br_interval(
            game,
            profile,
            args.player,
            prune_reach_threshold=threshold,
        )
        seconds = time.perf_counter() - started
        row = asdict(result)
        row["seconds"] = seconds
        row["contains_exact_br"] = (
            result.lower_br_value - TOLERANCE
            <= exact.value
            <= result.upper_br_value + TOLERANCE
        )
        row["exact_minus_lower"] = exact.value - result.lower_br_value
        row["upper_minus_exact"] = result.upper_br_value - exact.value
        if not row["contains_exact_br"]:
            raise SystemExit(
                f"interval containment failed at threshold {threshold}: "
                f"[{result.lower_br_value}, {result.upper_br_value}] vs {exact.value}"
            )
        if result.own_action_pruning_count != 0:
            raise SystemExit("own-action pruning firewall violated")
        rows.append(row)

    zero = rows[0]
    if zero["terminal_utility_evaluations"] != expected_terminals:
        raise SystemExit(
            "zero-threshold work mismatch: "
            f"{zero['terminal_utility_evaluations']} != {expected_terminals}"
        )
    if zero["pruned_opponent_branches"] != 0 or zero["state_local_envelope_calls"] != 0:
        raise SystemExit("zero threshold unexpectedly pruned a positive-reach uniform branch")
    if abs(zero["lower_br_value"] - exact.value) > TOLERANCE:
        raise SystemExit("zero-threshold lower value differs from exact BR")
    if abs(zero["upper_br_value"] - exact.value) > TOLERANCE:
        raise SystemExit("zero-threshold upper value differs from exact BR")

    positive = rows[1:]
    if not all(row["contains_exact_br"] for row in positive):
        raise SystemExit("positive-threshold exact containment failed")
    if not any(
        row["terminal_utility_evaluations"] < expected_terminals
        and row["state_local_envelope_calls"] > 0
        and row["pruned_opponent_branches"] > 0
        for row in positive
    ):
        raise SystemExit("positive thresholds failed to exercise conservative work reduction")

    unsigned = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "family": args.family,
        "player": args.player,
        "profile": "EMPTY_PROFILE_GAME_DEFINED_UNIFORM_FALLBACK",
        "thresholds": list(THRESHOLDS),
        "tolerance": TOLERANCE,
        "exact_reference": {
            "value": float(exact.value),
            "terminal_histories": int(exact.terminal_histories),
            "responding_infosets": len(exact.choices),
            "seconds": exact_seconds,
        },
        "intervals": rows,
        "decision": {
            "zero_threshold_exact": True,
            "all_intervals_contain_exact_br": True,
            "positive_threshold_work_reduction_exercised": True,
            "own_action_pruning_count": 0,
            "reduced_ladder_methodology_validated": True,
            "full_game_scalable_evaluator_validated": False,
            "production_certification_eligible": False,
            "real_routes_certified": 0,
        },
        "verdict": "PASS_M5R_THREE_ROUND_INTERVAL_BRIDGE_CELL",
        "production_certification_eligible": False,
        "real_routes_certified": 0,
    }
    payload = dict(unsigned)
    payload["sha256"] = _sha(unsigned)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "family": args.family,
        "player": args.player,
        "exact_br": exact.value,
        "intervals": [
            {
                "threshold": row["prune_reach_threshold"],
                "lower": row["lower_br_value"],
                "upper": row["upper_br_value"],
                "width": row["interval_width"],
                "terminal_evals": row["terminal_utility_evaluations"],
                "pruned": row["pruned_opponent_branches"],
            }
            for row in rows
        ],
        "sha256": payload["sha256"],
        "verdict": payload["verdict"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
