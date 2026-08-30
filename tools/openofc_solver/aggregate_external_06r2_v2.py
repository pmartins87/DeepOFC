from __future__ import annotations

"""Aggregate authority for EXT-06R2 V2 exact-exploitability cells."""

import argparse
import hashlib
import json
from pathlib import Path

EXPECTED_METHODS = ("MCCFR", "ISUCT")
EXPECTED_SEEDS = (20260830, 20260831)
EXPECTED_SCHEMA = "openofc-external-06r2-v2-cell-v1"
EXPECTED_TERMINALS = 839_808
TOL = 1e-9
MEAN_RATIO_GATE = 0.80


def _load(paths: list[Path]) -> dict[tuple[str, int], dict]:
    out: dict[tuple[str, int], dict] = {}
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema") != EXPECTED_SCHEMA:
            raise AssertionError(f"unexpected 06R2 schema in {path}")
        method = str(payload["method"])
        seed = int(payload["learner_seed"])
        key = (method, seed)
        if method not in EXPECTED_METHODS or seed not in EXPECTED_SEEDS:
            raise AssertionError(f"unexpected 06R2 cell {key}")
        if key in out:
            raise AssertionError(f"duplicate 06R2 cell {key}")
        if int(payload["training"]["terminal_evaluations"]) != EXPECTED_TERMINALS:
            raise AssertionError(f"terminal-work drift in {key}")
        if int(payload.get("real_routes_certified", -1)) != 0:
            raise AssertionError("06R2 cell exceeded authority boundary")
        if payload.get("verdict") != "PASS_06R2_CELL_NO_INDIVIDUAL_PROMOTION_AUTHORITY":
            raise AssertionError(f"06R2 cell did not pass: {key}")
        out[key] = payload

    expected = {(method, seed) for method in EXPECTED_METHODS for seed in EXPECTED_SEEDS}
    if set(out) != expected:
        raise AssertionError(f"incomplete 06R2 cell set: {sorted(out)}")
    return out


def run(paths: list[Path]) -> dict:
    cells = _load(paths)
    seed_rows = []
    strict_wins = {method: 0 for method in EXPECTED_METHODS}

    for seed in EXPECTED_SEEDS:
        values = {
            method: float(cells[(method, seed)]["exact_tribunal"]["exploitability"])
            for method in EXPECTED_METHODS
        }
        if values["MCCFR"] + TOL < values["ISUCT"]:
            winner = "MCCFR"
            strict_wins[winner] += 1
        elif values["ISUCT"] + TOL < values["MCCFR"]:
            winner = "ISUCT"
            strict_wins[winner] += 1
        else:
            winner = "TIE"
        seed_rows.append({
            "learner_seed": seed,
            "mccfr_exploitability": values["MCCFR"],
            "isuct_exploitability": values["ISUCT"],
            "strict_winner": winner,
        })

    means = {
        method: sum(
            float(cells[(method, seed)]["exact_tribunal"]["exploitability"])
            for seed in EXPECTED_SEEDS
        ) / len(EXPECTED_SEEDS)
        for method in EXPECTED_METHODS
    }

    ratios = {
        "MCCFR_vs_ISUCT": means["MCCFR"] / means["ISUCT"] if means["ISUCT"] > 0 else 0.0,
        "ISUCT_vs_MCCFR": means["ISUCT"] / means["MCCFR"] if means["MCCFR"] > 0 else 0.0,
    }

    promote_mccfr = (
        strict_wins["MCCFR"] == 2
        and strict_wins["ISUCT"] == 0
        and means["MCCFR"] <= MEAN_RATIO_GATE * means["ISUCT"] + TOL
    )
    promote_isuct = (
        strict_wins["ISUCT"] == 2
        and strict_wins["MCCFR"] == 0
        and means["ISUCT"] <= MEAN_RATIO_GATE * means["MCCFR"] + TOL
    )
    if promote_mccfr and promote_isuct:
        raise AssertionError("06R2 contract allowed two promoted methods")

    if promote_mccfr:
        verdict = "PROMOTE_MCCFR_FROM_06R2"
    elif promote_isuct:
        verdict = "PROMOTE_ISUCT_FROM_06R2"
    else:
        verdict = "NO_SINGLE_METHOD_PROMOTION_06R2"

    payload = {
        "schema": "openofc-external-06r2-v2-aggregate-v1",
        "experiment_id": "EXT-06R2-V2-EXACT-EXPLOITABILITY-AGGREGATE",
        "authority": "FROZEN_06R2_GLOBAL_PROMOTION_AUTHORITY",
        "terminal_evaluations_per_cell": EXPECTED_TERMINALS,
        "learner_seeds": list(EXPECTED_SEEDS),
        "primary_metric": "EXACT_EXPLOITABILITY",
        "strict_win_tolerance": TOL,
        "mean_ratio_gate": MEAN_RATIO_GATE,
        "seed_rows": seed_rows,
        "strict_wins": strict_wins,
        "mean_exploitability": means,
        "mean_ratios": ratios,
        "verdict": verdict,
        "real_routes_certified": 0,
    }
    payload["manifest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()
    return payload


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+", type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    payload = run(args.inputs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "verdict": payload["verdict"],
        "strict_wins": payload["strict_wins"],
        "mean_exploitability": payload["mean_exploitability"],
        "mean_ratios": payload["mean_ratios"],
        "manifest_sha256": payload["manifest_sha256"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
