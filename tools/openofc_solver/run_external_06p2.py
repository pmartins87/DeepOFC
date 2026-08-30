from __future__ import annotations

"""06P2 full-game R1 root stability/compute diagnostic."""

import argparse
import hashlib
import json
import math
from pathlib import Path
from time import perf_counter

from external_06p0_conditioned_uct import ConditionedSuitCanonicalISUCT
from external_06r0_conditioned_solver import (
    FROZEN_FIXTURES,
    ConditionedSuitCanonicalOutcomeSamplingMCCFR,
    build_conditioned_fixture,
    root_probe,
)
from external_06s0_suit_automorphism import (
    canonical_information_state,
    canonical_legal_action_keys,
)

EXPERIMENT_ID = "EXT-06P2-R1-ROOT-STABILITY-COMPUTE"
AUTHORITY = "FULL_GAME_R1_ROOT_STABILITY_COMPUTE_DIAGNOSTIC_ONLY"
SEEDS = (20260830, 20260831)
TERMINAL_BUDGETS = (512, 2_048, 8_192)
ISUCT_EXPLORATION = 2.0
MCCFR_EPSILON = 0.6


def _distribution_hash(distribution: dict[str, float]) -> str:
    raw = json.dumps(
        {key: float(distribution[key]) for key in sorted(distribution)},
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _validate_distribution(distribution: dict[str, float], expected_keys: tuple[str, ...]) -> bool:
    if set(distribution) != set(expected_keys):
        return False
    values = list(distribution.values())
    return (
        all(math.isfinite(value) and value >= 0.0 for value in values)
        and math.isclose(sum(values), 1.0, rel_tol=0.0, abs_tol=1e-9)
    )


def _entropy(distribution: dict[str, float]) -> float:
    return -sum(p * math.log(p) for p in distribution.values() if p > 0.0)


def _top_action(distribution: dict[str, float]) -> tuple[str, float]:
    key = min(distribution, key=lambda action: (-distribution[action], action))
    return key, distribution[key]


def _tv(a: dict[str, float], b: dict[str, float]) -> float:
    if set(a) != set(b):
        raise ValueError("TV requires identical action support")
    return 0.5 * sum(abs(a[key] - b[key]) for key in a)


def _isuct_distribution(solver: ConditionedSuitCanonicalISUCT) -> dict[str, float]:
    rows = solver.root_readout()
    total = sum(row.visits for row in rows)
    if total <= 0:
        raise RuntimeError("ISUCT root has no visits")
    return {
        row.canonical_action_key: row.visits / total
        for row in rows
    }


def _mccfr_distribution(
    solver: ConditionedSuitCanonicalOutcomeSamplingMCCFR,
    root_key: str,
) -> dict[str, float]:
    node = solver.nodes.get(root_key)
    if node is None:
        raise RuntimeError("MCCFR root node was not materialized")
    probabilities = node.average_policy()
    return {
        action: float(probability)
        for action, probability in zip(node.action_keys, probabilities)
    }


def _snapshot(
    *,
    method: str,
    seed: int,
    terminal_budget: int,
    runtime_seconds: float,
    stored_infosets: int,
    terminal_evaluations: int,
    distribution: dict[str, float],
    expected_keys: tuple[str, ...],
) -> dict:
    top, top_probability = _top_action(distribution)
    valid = _validate_distribution(distribution, expected_keys)
    return {
        "method": method,
        "seed": seed,
        "terminal_budget": terminal_budget,
        "runtime_seconds": runtime_seconds,
        "stored_information_states": stored_infosets,
        "terminal_evaluations": terminal_evaluations,
        "root_legal_action_count": len(expected_keys),
        "root_distribution": {key: distribution[key] for key in sorted(distribution)},
        "root_distribution_sha256": _distribution_hash(distribution),
        "top_root_action": top,
        "top_root_probability": top_probability,
        "root_entropy_nats": _entropy(distribution),
        "distribution_valid": valid,
        "terminal_budget_accounting_exact": terminal_evaluations == terminal_budget,
    }


def run() -> dict:
    started = perf_counter()
    spec = next(spec for spec in FROZEN_FIXTURES if spec.name == "R1_P0_A")
    root = build_conditioned_fixture(spec)
    root_key, _ = canonical_information_state(root)
    expected_keys = canonical_legal_action_keys(root)
    probe = root_probe(root, sample_seed=906201, samples=32)

    snapshots: list[dict] = []
    for seed in SEEDS:
        isuct = ConditionedSuitCanonicalISUCT(
            base_root=root,
            exploration=ISUCT_EXPLORATION,
            seed=seed,
            resample_future=True,
        )
        t0 = perf_counter()
        previous = 0
        for target in TERMINAL_BUDGETS:
            isuct.run(target - previous)
            elapsed = perf_counter() - t0
            distribution = _isuct_distribution(isuct)
            snapshots.append(_snapshot(
                method="ISUCT",
                seed=seed,
                terminal_budget=target,
                runtime_seconds=elapsed,
                stored_infosets=len(isuct.nodes),
                terminal_evaluations=isuct.terminal_evaluations,
                distribution=distribution,
                expected_keys=expected_keys,
            ))
            previous = target

        mccfr = ConditionedSuitCanonicalOutcomeSamplingMCCFR(
            base_root=root,
            resample_future=True,
            epsilon=MCCFR_EPSILON,
            seed=seed,
            cfr_plus=True,
        )
        t1 = perf_counter()
        previous_iterations = 0
        for target in TERMINAL_BUDGETS:
            target_iterations = target // 2
            if target_iterations * 2 != target:
                raise AssertionError("MCCFR terminal budget must be even")
            mccfr.run(target_iterations - previous_iterations)
            elapsed = perf_counter() - t1
            distribution = _mccfr_distribution(mccfr, root_key)
            snapshots.append(_snapshot(
                method="MCCFR",
                seed=seed,
                terminal_budget=target,
                runtime_seconds=elapsed,
                stored_infosets=len(mccfr.nodes),
                terminal_evaluations=mccfr.episodes,
                distribution=distribution,
                expected_keys=expected_keys,
            ))
            previous_iterations = target_iterations

    by_key = {
        (row["method"], row["seed"], row["terminal_budget"]): row
        for row in snapshots
    }
    cross_seed = []
    for method in ("ISUCT", "MCCFR"):
        for budget in TERMINAL_BUDGETS:
            a = by_key[(method, SEEDS[0], budget)]
            b = by_key[(method, SEEDS[1], budget)]
            cross_seed.append({
                "method": method,
                "terminal_budget": budget,
                "tv": _tv(a["root_distribution"], b["root_distribution"]),
                "same_top_action": a["top_root_action"] == b["top_root_action"],
                "seed_a_top": a["top_root_action"],
                "seed_b_top": b["top_root_action"],
            })

    within_seed = []
    for method in ("ISUCT", "MCCFR"):
        for seed in SEEDS:
            for previous, current in zip(TERMINAL_BUDGETS, TERMINAL_BUDGETS[1:]):
                a = by_key[(method, seed, previous)]
                b = by_key[(method, seed, current)]
                within_seed.append({
                    "method": method,
                    "seed": seed,
                    "from_terminal_budget": previous,
                    "to_terminal_budget": current,
                    "tv": _tv(a["root_distribution"], b["root_distribution"]),
                    "same_top_action": a["top_root_action"] == b["top_root_action"],
                })

    equal_budget_runtime = []
    for seed in SEEDS:
        for budget in TERMINAL_BUDGETS:
            uct = by_key[("ISUCT", seed, budget)]
            mccfr = by_key[("MCCFR", seed, budget)]
            equal_budget_runtime.append({
                "seed": seed,
                "terminal_budget": budget,
                "isuct_seconds": uct["runtime_seconds"],
                "mccfr_seconds": mccfr["runtime_seconds"],
                "mccfr_over_isuct_runtime_ratio": (
                    mccfr["runtime_seconds"] / uct["runtime_seconds"]
                    if uct["runtime_seconds"] > 0.0 else None
                ),
                "isuct_information_states": uct["stored_information_states"],
                "mccfr_information_states": mccfr["stored_information_states"],
            })

    quality = {
        "root_is_r1_p0": root.round_index == 1 and root.actor == 0,
        "root_information_firewall_exact": probe["raw_and_canonical_root_information_exact"],
        "resampling_changes_future": probe["unique_sampled_plan_sha256"] > 1,
        "root_action_set_nonempty": len(expected_keys) > 0,
        "snapshot_count_12": len(snapshots) == 12,
        "all_distributions_valid": all(row["distribution_valid"] for row in snapshots),
        "all_terminal_budget_accounting_exact": all(
            row["terminal_budget_accounting_exact"] for row in snapshots
        ),
        "all_methods_same_root_action_count": all(
            row["root_legal_action_count"] == len(expected_keys) for row in snapshots
        ),
        "real_routes_certified_zero": True,
    }
    passed = all(quality.values())

    payload = {
        "schema": "openofc-external-06p2-v1",
        "experiment_id": EXPERIMENT_ID,
        "authority": AUTHORITY,
        "fixture": {
            "name": spec.name,
            "seed": spec.seed,
            "round": root.round_index,
            "actor": root.actor,
            "canonical_root_key_sha256": hashlib.sha256(root_key.encode("utf-8")).hexdigest(),
            "root_legal_action_count": len(expected_keys),
            "future_sampler_probe": probe,
        },
        "frozen": {
            "seeds": list(SEEDS),
            "terminal_budgets": list(TERMINAL_BUDGETS),
            "isuct_exploration": ISUCT_EXPLORATION,
            "mccfr_epsilon": MCCFR_EPSILON,
            "mccfr_cfr_plus": True,
        },
        "snapshots": snapshots,
        "cross_seed_stability": cross_seed,
        "within_seed_budget_stability": within_seed,
        "equal_terminal_budget_runtime": equal_budget_runtime,
        "quality": quality,
        "verdict": (
            "PASS_06P2_R1_ROOT_STABILITY_COMPUTE_PROBE"
            if passed else "FAIL_06P2_R1_ROOT_STABILITY_COMPUTE_MECHANICS"
        ),
        "limitations": [
            "root stability is not strategic correctness",
            "GitHub-hosted wall clock is relative engineering calibration, not Ryzen 9 throughput",
            "only R1_P0 has the clean future-only belief guarantee used here",
            "no full-game exploitability or production authority is claimed",
        ],
        "real_routes_certified": 0,
        "runtime_seconds": perf_counter() - started,
    }
    payload["manifest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()
    if not passed:
        raise RuntimeError(json.dumps({
            "experiment_id": EXPERIMENT_ID,
            "verdict": payload["verdict"],
            "quality": quality,
        }, sort_keys=True))
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/external_06p2.json")
    args = parser.parse_args()
    payload = run()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "experiment_id": payload["experiment_id"],
        "verdict": payload["verdict"],
        "cross_seed_stability": payload["cross_seed_stability"],
        "equal_terminal_budget_runtime": payload["equal_terminal_budget_runtime"],
        "manifest_sha256": payload["manifest_sha256"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
