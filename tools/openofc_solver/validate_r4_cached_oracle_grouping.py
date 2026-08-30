from __future__ import annotations

"""Semantic regression for the memoized/direct R4 exact oracle.

Fixture 65109 is intentionally used because the previous cached accelerator
proved its old uniqueness assumption false there: multiple posterior worlds can
share one P1 information state. The optimized oracle must exactly match the
reference grouped oracle without granting P1 hidden-world knowledge.
"""

import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter

from external_06r0_conditioned_solver import ConditionedFixtureSpec, build_conditioned_fixture
from external_06r1_belief_correct import build_belief_support, exact_r4_p0_oracle
from r4_exact_oracle_cached import exact_r4_p0_oracle_cached

FIXTURE_SEED = 65109
TOL = 1e-12


def run() -> dict:
    spec = ConditionedFixtureSpec(f"R4F_{FIXTURE_SEED}", FIXTURE_SEED, 4, 0)
    root = build_conditioned_fixture(spec)
    support = build_belief_support(root, spec)

    started = perf_counter()
    reference = exact_r4_p0_oracle(root, spec, support)
    reference_seconds = perf_counter() - started

    started = perf_counter()
    optimized = exact_r4_p0_oracle_cached(root, spec, support)
    optimized_seconds = perf_counter() - started

    ref_values = reference.value_map()
    opt_values = optimized.value_map()
    if set(ref_values) != set(opt_values):
        raise AssertionError("optimized oracle changed root action set")
    max_abs_diff = max(abs(ref_values[k] - opt_values[k]) for k in ref_values)
    if max_abs_diff > TOL:
        raise AssertionError(f"optimized oracle value mismatch: {max_abs_diff}")
    if reference.posterior_worlds != optimized.posterior_worlds:
        raise AssertionError("optimized oracle changed posterior world count")
    if reference.p1_information_states_by_root_action != optimized.p1_information_states_by_root_action:
        raise AssertionError("optimized oracle changed P1 infoset grouping counts")
    if abs(reference.best_value - optimized.best_value) > TOL:
        raise AssertionError("optimized oracle changed best value")

    counts = dict(reference.p1_information_states_by_root_action)
    duplicate_world_grouping_proven = any(
        int(n_infos) < int(reference.posterior_worlds) for n_infos in counts.values()
    )
    if not duplicate_world_grouping_proven:
        raise AssertionError("fixture no longer exercises many-worlds-per-P1-infoset semantics")

    payload = {
        "schema": "openofc-r4-cached-oracle-grouping-regression-v1",
        "experiment_id": "EXT-06R1F-ORACLE-GROUPING-REGRESSION",
        "fixture_seed": FIXTURE_SEED,
        "posterior_worlds": reference.posterior_worlds,
        "p1_information_states_by_root_action": list(reference.p1_information_states_by_root_action),
        "duplicate_world_grouping_proven": duplicate_world_grouping_proven,
        "reference_best_action": reference.best_action_key,
        "optimized_best_action": optimized.best_action_key,
        "reference_best_value": reference.best_value,
        "optimized_best_value": optimized.best_value,
        "max_abs_root_action_value_diff": max_abs_diff,
        "reference_seconds": reference_seconds,
        "optimized_seconds": optimized_seconds,
        "verdict": "PASS_GROUPED_CACHED_ORACLE_SEMANTICS",
        "real_routes_certified": 0,
    }
    payload["manifest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()
    return payload


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    payload = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
