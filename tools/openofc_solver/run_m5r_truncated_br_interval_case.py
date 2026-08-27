from __future__ import annotations

"""Run one M5R-C reduced-game truncated-BR interval case."""

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from deepofc.hu_two_round_hidden_discard import HUTwoRoundHiddenDiscardSubgame
from deepofc.hu_two_round_joker import HUTwoRoundJokerSubgame
from m5q_support_range_feasibility import exact_terminal_utility_range
from m5r_truncated_br_interval import AUTHORITY, truncated_best_response_interval

SCHEMA = "openofc-m5r-truncated-br-interval-case-v1"


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _game(family: str):
    if family == "joker":
        return HUTwoRoundJokerSubgame()
    if family == "hidden-discard":
        return HUTwoRoundHiddenDiscardSubgame()
    raise ValueError(f"unsupported family: {family}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", choices=("joker", "hidden-discard"), required=True)
    ap.add_argument("--player", type=int, choices=(0, 1), required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    game = _game(args.family)
    profile = game.uniform_profile()
    utility = exact_terminal_utility_range(game)
    rows = [
        truncated_best_response_interval(
            game,
            profile,
            args.player,
            p0_utility_min=utility.minimum_p0_utility,
            p0_utility_max=utility.maximum_p0_utility,
            resolution_modulus=modulus,
        )
        for modulus in (16, 4, 1)
    ]

    widths = [row.interval_width for row in rows]
    if not (widths[0] + 1e-10 >= widths[1] and widths[1] + 1e-10 >= widths[2]):
        raise SystemExit(f"M5R-C nested interval widths did not contract: {widths}")
    if rows[-1].unresolved_terminal_histories != 0:
        raise SystemExit("M5R-C modulus=1 must resolve every positive-reach terminal history")
    if abs(rows[-1].lower_br_value - rows[-1].exact_br_value) > 1e-12:
        raise SystemExit("M5R-C full-resolution lower bound did not collapse to exact BR")
    if abs(rows[-1].upper_br_value - rows[-1].exact_br_value) > 1e-12:
        raise SystemExit("M5R-C full-resolution upper bound did not collapse to exact BR")

    unsigned: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "family": args.family,
        "player": args.player,
        "exact_p0_utility_range": {
            "minimum": utility.minimum_p0_utility,
            "maximum": utility.maximum_p0_utility,
            "range": utility.utility_range,
        },
        "rows": [asdict(row) for row in rows],
        "decision": {
            "rigorous_interval_algebra_validated_on_case": True,
            "subtree_pruning_work_saving_validated": False,
            "full_game_scalable_evaluator_validated": False,
            "production_certification_eligible": False,
            "real_routes_certified": 0,
            "next_blocker": "PREFIX_SUBTREE_REACH_MASS_PRUNING_WITH_RIGOROUS_REMAINDER_BOUND_MISSING",
        },
    }
    payload = dict(unsigned)
    payload["sha256"] = _sha(unsigned)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "family": args.family,
        "player": args.player,
        "sha256": payload["sha256"],
        "exact_br": rows[-1].exact_br_value,
        "widths": widths,
        "resolved": [row.resolved_terminal_histories for row in rows],
        "next_blocker": payload["decision"]["next_blocker"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
