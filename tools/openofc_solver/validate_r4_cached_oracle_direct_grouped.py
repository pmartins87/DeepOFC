from __future__ import annotations

"""Fast semantic regression for the memoized/direct R4 oracle.

Unlike validate_r4_cached_oracle_grouping.py, this check does not invoke the
slow prefix-replaying reference oracle. It independently recomputes the grouped
P1 best response over the SAME exact direct posterior worlds, but uses the
canonical child_state -> terminal_utility path rather than cached board scoring.

Fixture 65106 is frozen because 06R1F v2 already demonstrates that its posterior
contains fewer P1 infosets than posterior worlds, so the regression necessarily
exercises many-worlds-per-P1-infoset grouping.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
from time import perf_counter

from external_06r0_conditioned_solver import ConditionedFixtureSpec, build_conditioned_fixture
from external_06r1_belief_correct import _canonical_pairs, build_belief_support
from r4_exact_oracle_cached import exact_r4_p0_oracle_cached
from r4_exact_worlds_direct import iter_exact_r4_p0_worlds_direct
from strategic_cfr import child_state, information_state_key, legal_action_pairs, terminal_utility

FIXTURE_SEED = 65106
TOL = 1e-12


def _independent_direct_grouped(root, spec, support) -> dict:
    worlds = tuple(iter_exact_r4_p0_worlds_direct(root, spec, support, validate_each_world=True))
    if not worlds:
        raise AssertionError("empty direct posterior")
    world_count = len(worlds)
    root_key, root_pairs = _canonical_pairs(root)
    if root_key != support.root_canonical_information_state_key:
        raise AssertionError("root canonical key mismatch")

    values = {}
    counts = {}
    for canonical_root_action, _root_action in root_pairs:
        grouped: dict[str, dict[str, float]] = {}
        action_sets: dict[str, tuple[str, ...]] = {}
        for world in worlds:
            _world_key, world_pairs = _canonical_pairs(world)
            world_map = dict(world_pairs)
            child = child_state(world, world_map[canonical_root_action])
            if child.terminal() or (child.round_index, child.actor) != (4, 1):
                raise AssertionError("R4 P0 action did not lead to R4 P1")
            p1_key = information_state_key(child)
            pairs = tuple(legal_action_pairs(child))
            keys = tuple(key for key, _action in pairs)
            previous = action_sets.get(p1_key)
            if previous is None:
                action_sets[p1_key] = keys
                grouped[p1_key] = {key: 0.0 for key in keys}
            elif previous != keys:
                raise AssertionError("same P1 infoset changed legal action set")
            for p1_action_key, p1_action in pairs:
                terminal = child_state(child, p1_action)
                value = float(terminal_utility(terminal, 0))
                if not math.isfinite(value):
                    raise AssertionError("non-finite terminal utility")
                grouped[p1_key][p1_action_key] += value
        values[canonical_root_action] = (
            sum(min(action_sums.values()) for action_sums in grouped.values()) / world_count
        )
        counts[canonical_root_action] = len(grouped)
    return {
        "values": dict(sorted(values.items())),
        "counts": dict(sorted(counts.items())),
        "posterior_worlds": world_count,
    }


def run() -> dict:
    spec = ConditionedFixtureSpec(f"R4F_{FIXTURE_SEED}", FIXTURE_SEED, 4, 0)
    root = build_conditioned_fixture(spec)
    support = build_belief_support(root, spec)

    started = perf_counter()
    reference = _independent_direct_grouped(root, spec, support)
    reference_seconds = perf_counter() - started

    started = perf_counter()
    optimized = exact_r4_p0_oracle_cached(root, spec, support)
    optimized_seconds = perf_counter() - started

    opt_values = optimized.value_map()
    if set(reference["values"]) != set(opt_values):
        raise AssertionError("root action set mismatch")
    diffs = {
        key: abs(float(reference["values"][key]) - float(opt_values[key]))
        for key in reference["values"]
    }
    max_abs_diff = max(diffs.values()) if diffs else 0.0
    if max_abs_diff > TOL:
        raise AssertionError(f"cached oracle differs from independent grouped direct reference: {max_abs_diff}")

    opt_counts = dict(optimized.p1_information_states_by_root_action)
    if reference["counts"] != opt_counts:
        raise AssertionError("P1 infoset grouping counts mismatch")
    if reference["posterior_worlds"] != optimized.posterior_worlds:
        raise AssertionError("posterior world count mismatch")

    duplicate_world_grouping_proven = any(
        count < reference["posterior_worlds"] for count in reference["counts"].values()
    )
    if not duplicate_world_grouping_proven:
        raise AssertionError("fixture failed to exercise many-worlds-per-P1-infoset grouping")

    best_value = max(reference["values"].values())
    best_keys = sorted(
        key for key, value in reference["values"].items()
        if abs(value - best_value) <= TOL
    )
    if abs(float(optimized.best_value) - float(best_value)) > TOL:
        raise AssertionError("best value mismatch")
    if optimized.best_action_key not in best_keys:
        raise AssertionError("optimized best action is not reference-optimal")

    payload = {
        "schema": "openofc-r4-cached-oracle-direct-grouped-regression-v1",
        "experiment_id": "EXT-06R1F-ORACLE-DIRECT-GROUPING-REGRESSION",
        "fixture_seed": FIXTURE_SEED,
        "posterior_worlds": reference["posterior_worlds"],
        "p1_information_states_by_root_action": reference["counts"],
        "duplicate_world_grouping_proven": duplicate_world_grouping_proven,
        "reference_root_action_values": reference["values"],
        "optimized_root_action_values": opt_values,
        "max_abs_root_action_value_diff": max_abs_diff,
        "reference_best_value": best_value,
        "reference_best_action_keys": best_keys,
        "optimized_best_value": optimized.best_value,
        "optimized_best_action_key": optimized.best_action_key,
        "independent_reference_seconds": reference_seconds,
        "optimized_seconds": optimized_seconds,
        "verdict": "PASS_INDEPENDENT_DIRECT_GROUPED_ORACLE_SEMANTICS",
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
    print(json.dumps({
        "verdict": payload["verdict"],
        "fixture_seed": payload["fixture_seed"],
        "posterior_worlds": payload["posterior_worlds"],
        "p1_information_states_by_root_action": payload["p1_information_states_by_root_action"],
        "max_abs_root_action_value_diff": payload["max_abs_root_action_value_diff"],
        "manifest_sha256": payload["manifest_sha256"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
