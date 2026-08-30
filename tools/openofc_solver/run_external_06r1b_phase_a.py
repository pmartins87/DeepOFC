from __future__ import annotations

"""Frozen EXT-06R1B Phase-A exact multi-root R4 oracle panel."""

import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter

from external_06r0_conditioned_solver import ConditionedFixtureSpec, build_conditioned_fixture
from external_06r1_belief_correct import build_belief_support
from r4_exact_oracle_combinatorial import exact_r4_p0_oracle_combinatorial

EXPERIMENT_ID = "EXT-06R1B-R4-PANEL-PHASE-A"
SEEDS = tuple(range(64001, 64017))
NONDEGENERATE_EPS = 1e-9
MIN_NONDEGENERATE = 6


def run() -> dict:
    rows = []
    for seed in SEEDS:
        spec = ConditionedFixtureSpec(
            name=f"R4_P0_SEED_{seed}",
            seed=seed,
            round_index=4,
            actor=0,
        )
        root = build_conditioned_fixture(spec)
        support_started = perf_counter()
        support = build_belief_support(root, spec)
        support_seconds = perf_counter() - support_started
        oracle_started = perf_counter()
        oracle = exact_r4_p0_oracle_combinatorial(root, spec, support)
        oracle_seconds = perf_counter() - oracle_started
        values = dict(oracle.root_action_values)
        low = min(values.values())
        high = max(values.values())
        spread = high - low
        rows.append({
            "fixture": spec.name,
            "seed": seed,
            "root_action_count": len(values),
            "hidden_history_count": support.hidden_history_count,
            "posterior_worlds": oracle.posterior_worlds,
            "support_seconds": support_seconds,
            "oracle_seconds": oracle_seconds,
            "best_action_key": oracle.best_action_key,
            "best_value": oracle.best_value,
            "min_action_value": low,
            "max_action_value": high,
            "action_value_spread": spread,
            "classification": "NONDEGENERATE" if spread > NONDEGENERATE_EPS else "DEGENERATE",
            "root_action_values": values,
        })

    nondegenerate = [row for row in rows if row["classification"] == "NONDEGENERATE"]
    phase_b = len(nondegenerate) >= MIN_NONDEGENERATE
    verdict = (
        "PASS_06R1B_PHASE_A_ACTIVATE_METHOD_PANEL"
        if phase_b
        else "R4_RANDOM_PREFIX_PANEL_TOO_DEGENERATE"
    )
    payload = {
        "schema": "openofc-external-06r1b-phase-a-v1",
        "experiment_id": EXPERIMENT_ID,
        "frozen": {
            "fixture_seeds": list(SEEDS),
            "round": 4,
            "actor": 0,
            "prefix_policy": "PAYOFF_BLIND_HASHED_LEGAL_ACTION_V1",
            "oracle": "EXACT_R4_P0_COMBINATORIAL_V1",
            "nondegenerate_epsilon": NONDEGENERATE_EPS,
            "minimum_nondegenerate_for_phase_b": MIN_NONDEGENERATE,
        },
        "fixtures": rows,
        "summary": {
            "fixture_count": len(rows),
            "nondegenerate_count": len(nondegenerate),
            "degenerate_count": len(rows) - len(nondegenerate),
            "nondegenerate_seeds": [row["seed"] for row in nondegenerate],
            "phase_b_activated": phase_b,
            "total_support_seconds": sum(row["support_seconds"] for row in rows),
            "total_oracle_seconds": sum(row["oracle_seconds"] for row in rows),
        },
        "verdict": verdict,
        "real_routes_certified": 0,
    }
    payload["manifest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()
    return payload


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    payload = run()
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "experiment_id": payload["experiment_id"],
        "summary": payload["summary"],
        "verdict": payload["verdict"],
        "manifest_sha256": payload["manifest_sha256"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
