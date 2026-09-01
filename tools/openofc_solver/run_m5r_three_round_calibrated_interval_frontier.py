from __future__ import annotations

"""Run one pre-frozen M5R calibrated three-round BR interval frontier cell."""

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
from m5r_calibrated_threshold_manifest import (
    EXPECTED_REFERENCE,
    THRESHOLD_HEX_BY_FAMILY,
    manifest_payload,
    manifest_sha256,
    positive_thresholds,
)
from m5r_three_round_interval_bridge import conservative_three_round_br_interval

AUTHORITY = "M5R_REDUCED_CALIBRATED_INTERVAL_FRONTIER_ONLY_NOT_CERTIFICATION"
SCHEMA = "openofc-m5r-three-round-calibrated-interval-frontier-cell-v1"
TOLERANCE = 1e-10


def _case(family: str):
    if family == "three-round-v1":
        return HUThreeRoundSequentialSubgame()
    if family == "three-round-v2":
        return HUThreeRoundSequentialSubgameV2()
    raise ValueError(f"unsupported family: {family}")


def _sha(payload: object) -> str:
    raw = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", choices=("three-round-v1", "three-round-v2"), required=True)
    ap.add_argument("--player", type=int, choices=(0, 1), required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    game = _case(args.family)
    profile = {}
    expected = EXPECTED_REFERENCE[args.family][args.player]
    thresholds = positive_thresholds(args.family)
    threshold_hex = THRESHOLD_HEX_BY_FAMILY[args.family]

    started = time.perf_counter()
    exact = exact_best_response(game, profile, args.player)
    exact_seconds = time.perf_counter() - started

    expected_value = float(expected["exact_br_value"])
    expected_infosets = int(expected["responding_infosets"])
    expected_terminals = int(expected["terminal_histories"])
    if abs(float(exact.value) - expected_value) > TOLERANCE:
        raise SystemExit(
            f"exact BR drift: {exact.value} vs frozen {expected_value}"
        )
    if len(exact.choices) != expected_infosets:
        raise SystemExit(
            f"exact infoset drift: {len(exact.choices)} vs frozen {expected_infosets}"
        )
    if exact.terminal_histories != expected_terminals:
        raise SystemExit(
            f"exact terminal-history drift: {exact.terminal_histories} vs frozen {expected_terminals}"
        )

    rows: list[dict[str, object]] = [
        {
            "prune_reach_threshold": 0.0,
            "prune_reach_threshold_hex": "0x0.0p+0",
            "source": "EXACT_BR_REFERENCE_ZERO_THRESHOLD_BASELINE",
            "lower_br_value": float(exact.value),
            "upper_br_value": float(exact.value),
            "interval_width": 0.0,
            "terminal_utility_evaluations": expected_terminals,
            "terminal_work_fraction": 1.0,
            "pruned_opponent_branches": 0,
            "state_local_envelope_calls": 0,
            "own_action_pruning_count": 0,
            "contains_exact_br": True,
            "exact_minus_lower": 0.0,
            "upper_minus_exact": 0.0,
            "seconds": exact_seconds,
        }
    ]

    previous_work = expected_terminals
    for frozen_hex, threshold in zip(threshold_hex, thresholds, strict=True):
        if threshold.hex() != frozen_hex:
            raise SystemExit(
                f"threshold binary identity drift: {threshold.hex()} != {frozen_hex}"
            )
        started = time.perf_counter()
        result = conservative_three_round_br_interval(
            game,
            profile,
            args.player,
            prune_reach_threshold=threshold,
        )
        seconds = time.perf_counter() - started
        contains = (
            result.lower_br_value - TOLERANCE
            <= exact.value
            <= result.upper_br_value + TOLERANCE
        )
        if not contains:
            raise SystemExit(
                f"exact BR escaped interval at threshold {frozen_hex}: "
                f"[{result.lower_br_value}, {result.upper_br_value}] vs {exact.value}"
            )
        if result.own_action_pruning_count != 0:
            raise SystemExit("responding-player action pruning firewall violated")
        if result.terminal_utility_evaluations > previous_work:
            raise SystemExit(
                "terminal work increased with increasing threshold: "
                f"{result.terminal_utility_evaluations} > {previous_work}"
            )
        previous_work = result.terminal_utility_evaluations

        row = asdict(result)
        row.update(
            {
                "prune_reach_threshold_hex": frozen_hex,
                "source": "CONSERVATIVE_INTERVAL_AT_PRE_FROZEN_REACH_BREAKPOINT",
                "terminal_work_fraction": (
                    result.terminal_utility_evaluations / expected_terminals
                ),
                "contains_exact_br": True,
                "exact_minus_lower": exact.value - result.lower_br_value,
                "upper_minus_exact": result.upper_br_value - exact.value,
                "seconds": seconds,
            }
        )
        rows.append(row)

    positive = rows[1:]
    if not positive:
        raise SystemExit("frozen positive threshold panel is empty")
    if not any(
        int(row["terminal_utility_evaluations"]) < expected_terminals
        for row in positive
    ):
        raise SystemExit("calibrated positive thresholds did not reduce work")
    if not all(bool(row["contains_exact_br"]) for row in positive):
        raise SystemExit("calibrated interval containment failed")

    unsigned = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "family": args.family,
        "player": args.player,
        "profile": "EMPTY_PROFILE_GAME_DEFINED_UNIFORM_FALLBACK",
        "threshold_manifest_sha256": manifest_sha256(),
        "threshold_manifest": manifest_payload(),
        "threshold_selection_rule": (
            "ALL_DISTINCT_POSITIVE_OPPONENT_COUNTERFACTUAL_REACH_LEVELS_"
            "OBSERVED_PER_FAMILY_BEFORE_FRONTIER_EXECUTION"
        ),
        "tolerance": TOLERANCE,
        "exact_reference": {
            "value": float(exact.value),
            "terminal_histories": int(exact.terminal_histories),
            "responding_infosets": len(exact.choices),
            "seconds": exact_seconds,
        },
        "frontier": rows,
        "summary": {
            "positive_thresholds": len(positive),
            "minimum_positive_interval_width": min(
                float(row["interval_width"]) for row in positive
            ),
            "maximum_positive_interval_width": max(
                float(row["interval_width"]) for row in positive
            ),
            "minimum_positive_terminal_work_fraction": min(
                float(row["terminal_work_fraction"]) for row in positive
            ),
            "maximum_positive_terminal_work_fraction": max(
                float(row["terminal_work_fraction"]) for row in positive
            ),
        },
        "decision": {
            "exact_reference_reproduced": True,
            "all_intervals_contain_exact_br": True,
            "terminal_work_nonincreasing": True,
            "positive_work_reduction_exercised": True,
            "own_action_pruning_count": 0,
            "calibrated_reduced_frontier_measured": True,
            "production_threshold_selected": False,
            "full_game_scalable_evaluator_validated": False,
            "production_certification_eligible": False,
            "real_routes_certified": 0,
        },
        "verdict": "PASS_M5R_CALIBRATED_INTERVAL_FRONTIER_CELL",
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

    print(
        json.dumps(
            {
                "family": args.family,
                "player": args.player,
                "exact_br": exact.value,
                "threshold_manifest_sha256": manifest_sha256(),
                "frontier": [
                    {
                        "threshold_hex": row["prune_reach_threshold_hex"],
                        "width": row["interval_width"],
                        "terminal_work_fraction": row["terminal_work_fraction"],
                    }
                    for row in rows
                ],
                "verdict": payload["verdict"],
                "sha256": payload["sha256"],
                "real_routes_certified": 0,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
