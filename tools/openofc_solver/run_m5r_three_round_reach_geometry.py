from __future__ import annotations

"""Run one frozen M5R three-round opponent-reach geometry cell."""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepofc.hu_three_round_sequential import HUThreeRoundSequentialSubgame
from deepofc.hu_three_round_sequential_v2 import HUThreeRoundSequentialSubgameV2
from m5r_three_round_reach_geometry import (
    AUTHORITY,
    SCHEMA,
    opponent_reach_geometry,
)


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _case(family: str):
    if family == "three-round-v1":
        return HUThreeRoundSequentialSubgame(), 1_312_200
    if family == "three-round-v2":
        return HUThreeRoundSequentialSubgameV2(), 839_808
    raise ValueError(f"unsupported family: {family}")


def _rows(levels):
    return [
        {
            "float_hex": row.float_hex,
            "value": float(row.value),
            "count": int(row.count),
        }
        for row in levels
    ]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", choices=("three-round-v1", "three-round-v2"), required=True)
    ap.add_argument("--player", type=int, choices=(0, 1), required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    game, expected_terminal_histories = _case(args.family)
    profile = {}

    started = time.perf_counter()
    result = opponent_reach_geometry(game, profile, args.player)
    seconds = time.perf_counter() - started

    if result.terminal_histories != expected_terminal_histories:
        raise SystemExit(
            f"terminal coverage mismatch: {result.terminal_histories} vs {expected_terminal_histories}"
        )
    if result.candidate_opponent_children <= 0:
        raise SystemExit("no legal cut-candidate opponent children")
    if not result.positive_reach_levels:
        raise SystemExit("no positive reach levels")
    if result.responding_player_probability_multiplications != 0:
        raise SystemExit("responding-player probabilities entered counterfactual reach")
    if result.pruning_executed:
        raise SystemExit("geometry gate must not prune")

    positive = result.positive_reach_levels
    unsigned = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "family": args.family,
        "player": args.player,
        "profile": "EMPTY_UNIFORM_PROFILE",
        "terminal_histories": result.terminal_histories,
        "expected_terminal_histories": expected_terminal_histories,
        "candidate_opponent_children": result.candidate_opponent_children,
        "zero_reach_candidates": result.zero_reach_candidates,
        "distinct_positive_reach_levels": len(positive),
        "min_positive_reach": float(positive[0].value),
        "max_positive_reach": float(positive[-1].value),
        "positive_reach_levels": _rows(positive),
        "positive_reach_levels_by_round": {
            str(round_index): _rows(rows)
            for round_index, rows in result.positive_reach_levels_by_round.items()
        },
        "responding_player_probability_multiplications": 0,
        "pruning_executed": False,
        "seconds": seconds,
        "validation_status": "PASS",
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
        "candidate_opponent_children": result.candidate_opponent_children,
        "distinct_positive_reach_levels": len(positive),
        "min_positive_reach": positive[0].value,
        "max_positive_reach": positive[-1].value,
        "terminal_histories": result.terminal_histories,
        "seconds": seconds,
        "validation_status": "PASS",
        "sha256": payload["sha256"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()