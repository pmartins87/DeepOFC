from __future__ import annotations

"""Aggregate authority for EXT-06R1F.

Input is the complete set of twelve per-fixture JSON artifacts produced by
run_external_06r1f.py. The promotion rule is the rule frozen in 06R1E/06R1F;
mixed-policy regret is reported only as a secondary diagnostic.
"""

import argparse
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

EXPECTED_FIXTURE_SEEDS = tuple(range(65101, 65113))
EXPECTED_BUDGETS = (32, 64, 128, 256, 512, 1024)
EXPECTED_LEARNER_SEEDS = (20260830, 20260831)
EXPECTED_SCHEMA = "openofc-external-06r1f-v2"
EXPECTED_ORACLE_SEMANTICS = "P1_INFOSET_GROUPED_BEST_RESPONSE_V2"
TOP_TOL = 1e-9
DISCRIMINATION_TOL = 1e-12


def _load(paths: list[Path]) -> list[dict]:
    payloads = [json.loads(p.read_text(encoding="utf-8")) for p in paths]
    by_seed = {}
    for payload in payloads:
        if payload.get("schema") != EXPECTED_SCHEMA:
            raise AssertionError("unexpected 06R1F schema")
        if payload.get("oracle_semantics") != EXPECTED_ORACLE_SEMANTICS:
            raise AssertionError("06R1F oracle semantics drift")
        seed = int(payload["r1f_fixture"]["seed"])
        if seed in by_seed:
            raise AssertionError(f"duplicate fixture seed {seed}")
        by_seed[seed] = payload
    if tuple(sorted(by_seed)) != EXPECTED_FIXTURE_SEEDS:
        raise AssertionError(
            f"incomplete or unexpected fixture suite: {tuple(sorted(by_seed))}"
        )
    return [by_seed[s] for s in EXPECTED_FIXTURE_SEEDS]


def _stable_hit(payload: dict, method: str, learner_seed: int) -> int | None:
    row = next(
        x for x in payload["stable_hits"]
        if x["method"] == method and int(x["learner_seed"]) == learner_seed
    )
    value = row["stable_hit_budget"]
    return None if value is None else int(value)


def _as_rank(value: int | None) -> float:
    return math.inf if value is None else float(value)


def run(paths: list[Path]) -> dict:
    payloads = _load(paths)

    for payload in payloads:
        frozen = payload["frozen"]
        if tuple(int(x) for x in frozen["terminal_budgets"]) != EXPECTED_BUDGETS:
            raise AssertionError("budget drift")
        if tuple(int(x) for x in frozen["learner_seeds"]) != EXPECTED_LEARNER_SEEDS:
            raise AssertionError("learner-seed drift")
        contract = payload["global_promotion_contract"]
        if tuple(int(x) for x in contract["fixture_seeds"]) != EXPECTED_FIXTURE_SEEDS:
            raise AssertionError("fixture contract drift")

    discriminative = [
        p for p in payloads
        if float(p["r1f_fixture"]["oracle_action_value_spread"]) > DISCRIMINATION_TOL
    ]

    pair_rows = []
    wins = defaultdict(int)
    wins_by_seed = defaultdict(lambda: defaultdict(int))
    ties = 0
    for payload in discriminative:
        fixture_seed = int(payload["r1f_fixture"]["seed"])
        for learner_seed in EXPECTED_LEARNER_SEEDS:
            iu = _stable_hit(payload, "ISUCT", learner_seed)
            mc = _stable_hit(payload, "MCCFR", learner_seed)
            if _as_rank(iu) < _as_rank(mc):
                winner = "ISUCT"
                wins["ISUCT"] += 1
                wins_by_seed[learner_seed]["ISUCT"] += 1
            elif _as_rank(mc) < _as_rank(iu):
                winner = "MCCFR"
                wins["MCCFR"] += 1
                wins_by_seed[learner_seed]["MCCFR"] += 1
            else:
                winner = "TIE"
                ties += 1
            pair_rows.append({
                "fixture_seed": fixture_seed,
                "learner_seed": learner_seed,
                "isuct_stable_hit_budget": iu,
                "mccfr_stable_hit_budget": mc,
                "winner": winner,
            })

    final_hits = defaultdict(int)
    final_total = len(discriminative) * len(EXPECTED_LEARNER_SEEDS)
    secondary_policy_regrets = defaultdict(list)
    for payload in discriminative:
        for cell in payload["cells"]:
            if int(cell["terminal_budget"]) != 1024:
                continue
            method = cell["method"]
            if float(cell["exact_local_top_action_regret"]) <= TOP_TOL:
                final_hits[method] += 1
            secondary_policy_regrets[method].append(float(cell["exact_local_policy_regret"]))

    hit_rates = {
        method: (final_hits[method] / final_total if final_total else 0.0)
        for method in ("ISUCT", "MCCFR")
    }

    def qualifies(method: str, other: str) -> bool:
        if len(discriminative) < 6:
            return False
        mw = int(wins[method])
        ow = int(wins[other])
        if mw < 4:
            return False
        if mw < 2 * ow:
            return False
        for learner_seed in EXPECTED_LEARNER_SEEDS:
            if wins_by_seed[learner_seed][method] < wins_by_seed[learner_seed][other]:
                return False
        if hit_rates[method] + 1e-15 < hit_rates[other]:
            return False
        return True

    q_isuct = qualifies("ISUCT", "MCCFR")
    q_mccfr = qualifies("MCCFR", "ISUCT")
    if q_isuct and q_mccfr:
        raise AssertionError("promotion contract allowed two winners")
    if len(discriminative) < 6:
        verdict = "INSUFFICIENT_DISCRIMINATIVE_FIXTURES_REDESIGN"
    elif q_isuct:
        verdict = "PROMOTE_ISUCT_TO_06R2"
    elif q_mccfr:
        verdict = "PROMOTE_MCCFR_TO_06R2"
    else:
        verdict = "NO_PROMOTION_06R1F"

    secondary = {}
    for method in ("ISUCT", "MCCFR"):
        rows = secondary_policy_regrets[method]
        secondary[method] = {
            "budget_1024_mean_exact_local_policy_regret": (
                sum(rows) / len(rows) if rows else None
            ),
            "n": len(rows),
        }

    payload = {
        "schema": "openofc-external-06r1f-aggregate-v2",
        "experiment_id": "EXT-06R1F-R4-TOP-ACTION-SAMPLE-EFFICIENCY-AGGREGATE",
        "authority": "FROZEN_06R1F_GLOBAL_PROMOTION_AUTHORITY",
        "oracle_semantics": EXPECTED_ORACLE_SEMANTICS,
        "fixture_seeds": list(EXPECTED_FIXTURE_SEEDS),
        "terminal_budgets": list(EXPECTED_BUDGETS),
        "learner_seeds": list(EXPECTED_LEARNER_SEEDS),
        "discriminative_fixture_count": len(discriminative),
        "discriminative_fixture_seeds": [int(p["r1f_fixture"]["seed"]) for p in discriminative],
        "strict_stable_hit_wins": {
            "ISUCT": int(wins["ISUCT"]),
            "MCCFR": int(wins["MCCFR"]),
            "TIE": int(ties),
        },
        "strict_wins_by_learner_seed": {
            str(seed): {
                "ISUCT": int(wins_by_seed[seed]["ISUCT"]),
                "MCCFR": int(wins_by_seed[seed]["MCCFR"]),
            }
            for seed in EXPECTED_LEARNER_SEEDS
        },
        "budget_1024_oracle_optimal_top_action_hits": {
            "denominator": final_total,
            "ISUCT": int(final_hits["ISUCT"]),
            "MCCFR": int(final_hits["MCCFR"]),
            "ISUCT_rate": hit_rates["ISUCT"],
            "MCCFR_rate": hit_rates["MCCFR"],
        },
        "pair_rows": pair_rows,
        "secondary_mixed_policy_diagnostic": secondary,
        "secondary_has_promotion_authority": False,
        "promotion_contract": {
            "minimum_discriminative_fixtures": 6,
            "minimum_strict_stable_hit_wins": 4,
            "strict_win_ratio_required_vs_competitor": 2.0,
            "require_nonreversal_within_each_learner_seed": True,
            "require_no_lower_1024_oracle_optimal_hit_rate": True,
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
    ap.add_argument("inputs", nargs="+", type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    payload = run(args.inputs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "verdict": payload["verdict"],
        "discriminative_fixture_count": payload["discriminative_fixture_count"],
        "strict_stable_hit_wins": payload["strict_stable_hit_wins"],
        "budget_1024_hits": payload["budget_1024_oracle_optimal_top_action_hits"],
        "manifest_sha256": payload["manifest_sha256"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
