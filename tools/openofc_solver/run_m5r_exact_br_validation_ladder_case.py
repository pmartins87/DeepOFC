from __future__ import annotations

"""Run one exact three-round BR validation-ladder case."""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepofc.hu_three_round_br import exact_best_response, exact_value_of_pure_response
from deepofc.hu_three_round_sequential import HUThreeRoundSequentialSubgame
from deepofc.hu_three_round_sequential_v2 import HUThreeRoundSequentialSubgameV2

AUTHORITY = "M5R_EXACT_THREE_ROUND_BR_VALIDATION_LADDER_NOT_ROUTE_CERTIFICATION"
SCHEMA = "openofc-m5r-exact-br-validation-ladder-case-v1"


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _case(family: str):
    if family == "three-round-v1":
        return HUThreeRoundSequentialSubgame(), 1_312_200, 8 * 405
    if family == "three-round-v2":
        return HUThreeRoundSequentialSubgameV2(), 839_808, 32 * 162
    raise ValueError(f"unsupported M5R ladder family: {family}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", choices=("three-round-v1", "three-round-v2"), required=True)
    ap.add_argument("--player", type=int, choices=(0, 1), required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    game, expected_br_terminals, expected_replay_terminals = _case(args.family)
    profile = {}

    started = time.perf_counter()
    response = exact_best_response(game, profile, args.player)
    br_seconds = time.perf_counter() - started
    if response.terminal_histories != expected_br_terminals:
        raise SystemExit(
            f"{args.family} BR{args.player} coverage mismatch: "
            f"{response.terminal_histories} vs {expected_br_terminals}"
        )

    started = time.perf_counter()
    replay_value, replay_terminals = exact_value_of_pure_response(game, profile, response)
    replay_seconds = time.perf_counter() - started
    if replay_terminals != expected_replay_terminals:
        raise SystemExit(
            f"{args.family} replay coverage mismatch: {replay_terminals} vs {expected_replay_terminals}"
        )
    cross_error = abs(float(response.value) - float(replay_value))
    if cross_error > 1e-10:
        raise SystemExit(
            f"{args.family} BR{args.player} replay mismatch: {response.value} vs {replay_value}"
        )

    expected_infos = sum(1 for info in game.info_actions if info.player == args.player)
    if len(response.choices) != expected_infos:
        raise SystemExit(
            f"{args.family} BR{args.player} infoset coverage mismatch: "
            f"{len(response.choices)} vs {expected_infos}"
        )

    unsigned: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "family": args.family,
        "player": args.player,
        "exact_br_value": float(response.value),
        "independent_pure_replay_value": float(replay_value),
        "crosscheck_abs_error": cross_error,
        "responding_infosets": len(response.choices),
        "expected_responding_infosets": expected_infos,
        "exact_br_terminal_histories": response.terminal_histories,
        "expected_exact_br_terminal_histories": expected_br_terminals,
        "pure_replay_terminal_histories": replay_terminals,
        "expected_pure_replay_terminal_histories": expected_replay_terminals,
        "br_seconds": br_seconds,
        "replay_seconds": replay_seconds,
        "validation_status": "PASS",
        "production_certification_eligible": False,
        "real_routes_certified": 0,
    }
    payload = dict(unsigned)
    payload["sha256"] = _sha(unsigned)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
