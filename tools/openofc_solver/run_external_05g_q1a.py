from __future__ import annotations

"""Run 05G-Q1A native provenance/router materialization.

This gate freezes native Search/MCCFR source ownership over the exhaustive 05G
support.  It deliberately performs no policy completion, exact profile EV,
best response, NashConv, exploitability, or strategic ranking.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
from statistics import median
from time import perf_counter
from typing import Mapping, Sequence

from external_05g_broad_support import (
    AUTHORITY,
    broad_worlds,
    public_pre_r3_state,
    support_sha256,
    validate_broad_physical_support,
)
from external_hidden_discard_overlap import run_overlap_infoset_uct
from external_hidden_discard_overlap_strategic import (
    OverlapExternalSamplingMCCFR,
    ReachableSupport,
    build_reachable_support,
    visit_profile_from_overlap_search,
)
from run_external_05g_q0b import _support_maps, _validate_profile
from run_external_05g_q0d import BUDGETS as Q0D_TESTED_BUDGETS

EXPERIMENT_ID = "EXT-05G-Q1A-NATIVE-PROVENANCE-ROUTER"
SEEDS = (20260829, 20260830)
SEARCH_ITERATIONS = 50_000
SEARCH_EXPLORATION = 1.0
MCCFR_ITERATIONS = 1_024
Q0D_SELECTION_REASON = (
    "smallest_tested_budget_meeting_80pct_nonroot_and_95pct_ambiguous_on_both_seeds"
)

SEARCH_NATIVE = "SEARCH_NATIVE"
MCCFR_NATIVE = "MCCFR_NATIVE"
MISSING = "MISSING"

BehaviorProfile = Mapping[str, Mapping[str, float]]


def _profile_sha256(profile: BehaviorProfile) -> str:
    digest = hashlib.sha256()
    for info_key in sorted(profile):
        digest.update(hashlib.sha256(info_key.encode("utf-8")).digest())
        digest.update(b"\0")
        for action_key in sorted(profile[info_key]):
            digest.update(action_key.encode("utf-8"))
            digest.update(b"=")
            digest.update(format(float(profile[info_key][action_key]), ".17g").encode("ascii"))
            digest.update(b";")
        digest.update(b"\n")
    return digest.hexdigest()


def _source_map_sha256(source_map: Mapping[str, str]) -> str:
    digest = hashlib.sha256()
    for info_key in sorted(source_map):
        digest.update(hashlib.sha256(info_key.encode("utf-8")).digest())
        digest.update(b"=")
        digest.update(source_map[info_key].encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _layer_name(row: ReachableSupport) -> str:
    return f"R{row.round_index}_P{row.actor}"


def _source_accounting(
    source_map: Mapping[str, str],
    support_rows: Sequence[ReachableSupport],
) -> dict:
    allowed = {SEARCH_NATIVE, MCCFR_NATIVE, MISSING}
    exhaustive = {row.information_state_key for row in support_rows}
    if set(source_map) != exhaustive:
        raise AssertionError("source map does not cover exhaustive support exactly")
    if any(label not in allowed for label in source_map.values()):
        raise AssertionError("source map contains undeclared source label")

    overall = {label: 0 for label in sorted(allowed)}
    by_layer: dict[str, dict[str, int]] = {}
    ambiguous_nonroot = {label: 0 for label in sorted(allowed)}
    for row in support_rows:
        label = source_map[row.information_state_key]
        overall[label] += 1
        layer = _layer_name(row)
        bucket = by_layer.setdefault(layer, {name: 0 for name in sorted(allowed)})
        bucket[label] += 1
        if (row.round_index, row.actor) != (3, 0) and len(row.concrete_states) > 1:
            ambiguous_nonroot[label] += 1

    total = len(support_rows)
    return {
        "exhaustive_information_states": total,
        "counts": overall,
        "percentages": {key: value / total for key, value in overall.items()},
        "counts_by_layer": {key: by_layer[key] for key in sorted(by_layer)},
        "ambiguous_nonroot_counts": ambiguous_nonroot,
        "source_map_sha256": _source_map_sha256(source_map),
    }


def _tv(a: Mapping[str, float], b: Mapping[str, float]) -> float:
    legal = sorted(set(a) | set(b))
    return 0.5 * sum(abs(float(a.get(key, 0.0)) - float(b.get(key, 0.0))) for key in legal)


def _percentile_nearest_rank(values: Sequence[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(x) for x in values)
    rank = max(1, math.ceil(fraction * len(ordered)))
    return ordered[rank - 1]


def _shared_diagnostics(search: BehaviorProfile, mccfr: BehaviorProfile) -> dict:
    shared = sorted(set(search) & set(mccfr))
    tvs = [_tv(search[key], mccfr[key]) for key in shared]
    top_agree = 0
    for key in shared:
        s_top = max(search[key], key=lambda action: (float(search[key][action]), action))
        m_top = max(mccfr[key], key=lambda action: (float(mccfr[key][action]), action))
        top_agree += int(s_top == m_top)
    return {
        "shared_native_information_states": len(shared),
        "mean_tv": sum(tvs) / len(tvs) if tvs else 0.0,
        "median_tv": median(tvs) if tvs else 0.0,
        "p95_tv": _percentile_nearest_rank(tvs, 0.95),
        "max_tv": max(tvs, default=0.0),
        "top_action_agreement_count": top_agree,
        "top_action_agreement_ratio": top_agree / len(shared) if shared else 0.0,
        "diagnostic_only_not_ranking": True,
    }


def _assemble_maps(
    support_rows: Sequence[ReachableSupport],
    search: BehaviorProfile,
    mccfr: BehaviorProfile,
) -> tuple[dict[str, str], dict[str, str], dict[str, str], dict[str, dict[str, float]]]:
    search_keys = set(search)
    mccfr_keys = set(mccfr)
    s_map: dict[str, str] = {}
    m_map: dict[str, str] = {}
    h_map: dict[str, str] = {}
    hybrid: dict[str, dict[str, float]] = {}

    for row in support_rows:
        key = row.information_state_key
        s_map[key] = SEARCH_NATIVE if key in search_keys else MISSING
        m_map[key] = MCCFR_NATIVE if key in mccfr_keys else MISSING
        if key in search_keys:
            h_map[key] = SEARCH_NATIVE
            hybrid[key] = {action: float(prob) for action, prob in search[key].items()}
        elif key in mccfr_keys:
            h_map[key] = MCCFR_NATIVE
            hybrid[key] = {action: float(prob) for action, prob in mccfr[key].items()}
        else:
            h_map[key] = MISSING

    return s_map, m_map, h_map, hybrid


def _native_preservation(
    search: BehaviorProfile,
    mccfr: BehaviorProfile,
    h_map: Mapping[str, str],
    hybrid: BehaviorProfile,
) -> dict:
    search_ok = all(
        h_map[key] == SEARCH_NATIVE
        and key in hybrid
        and dict(hybrid[key]) == {action: float(prob) for action, prob in search[key].items()}
        for key in search
    )
    mccfr_backfill_keys = set(mccfr) - set(search)
    mccfr_ok = all(
        h_map[key] == MCCFR_NATIVE
        and key in hybrid
        and dict(hybrid[key]) == {action: float(prob) for action, prob in mccfr[key].items()}
        for key in mccfr_backfill_keys
    )
    no_mccfr_overwrite = all(h_map[key] == SEARCH_NATIVE for key in set(search) & set(mccfr))
    return {
        "search_native_preserved_exactly": search_ok,
        "mccfr_backfill_preserved_exactly": mccfr_ok,
        "mccfr_never_overwrites_search": no_mccfr_overwrite,
        "search_native_keys": len(search),
        "mccfr_backfill_keys": len(mccfr_backfill_keys),
        "hybrid_native_keys": len(hybrid),
        "hybrid_profile_sha256": _profile_sha256(hybrid),
    }


def _run_seed(
    *,
    seed: int,
    base_state,
    worlds,
    support_rows: Sequence[ReachableSupport],
    support_by_key: Mapping[str, ReachableSupport],
) -> dict:
    world_ids = tuple(world.world_id for world in worlds)

    t0 = perf_counter()
    search_result = run_overlap_infoset_uct(
        base_state,
        worlds,
        iterations=SEARCH_ITERATIONS,
        seed=seed,
        exploration=SEARCH_EXPLORATION,
    )
    search_seconds = perf_counter() - t0
    search = visit_profile_from_overlap_search(search_result)

    t1 = perf_counter()
    solver = OverlapExternalSamplingMCCFR(base_state, worlds, seed=seed)
    solver.run(MCCFR_ITERATIONS)
    mccfr_seconds = perf_counter() - t1
    mccfr = solver.current_profile()
    mccfr_snapshot = solver.snapshot()

    search_validation = _validate_profile(search, support_by_key, world_ids)
    mccfr_validation = _validate_profile(mccfr, support_by_key, world_ids)
    s_map, m_map, h_map, hybrid = _assemble_maps(support_rows, search, mccfr)
    s_accounting = _source_accounting(s_map, support_rows)
    m_accounting = _source_accounting(m_map, support_rows)
    h_accounting = _source_accounting(h_map, support_rows)
    preservation = _native_preservation(search, mccfr, h_map, hybrid)

    search_keys = set(search)
    mccfr_keys = set(mccfr)
    overlap = {
        "search_intersection_mccfr": len(search_keys & mccfr_keys),
        "search_only": len(search_keys - mccfr_keys),
        "mccfr_only": len(mccfr_keys - search_keys),
        "neither": len(set(s_map) - (search_keys | mccfr_keys)),
    }

    validation_pass = all(
        validation[field] == 0
        for validation in (search_validation, mccfr_validation)
        for field in (
            "illegal_key_count",
            "action_set_mismatch_count",
            "invalid_distribution_count",
            "hidden_world_token_leakage_count",
        )
    )
    arithmetic_pass = all(
        sum(accounting["counts"].values()) == len(support_rows)
        for accounting in (s_accounting, m_accounting, h_accounting)
    )
    source_semantics_pass = all((
        s_accounting["counts"][SEARCH_NATIVE] == len(search),
        s_accounting["counts"][MCCFR_NATIVE] == 0,
        m_accounting["counts"][MCCFR_NATIVE] == len(mccfr),
        m_accounting["counts"][SEARCH_NATIVE] == 0,
        h_accounting["counts"][SEARCH_NATIVE] == len(search),
        h_accounting["counts"][MCCFR_NATIVE] == len(mccfr_keys - search_keys),
        h_accounting["counts"][MISSING] == overlap["neither"],
    ))

    return {
        "seed": seed,
        "budgets": {
            "search_iterations": SEARCH_ITERATIONS,
            "search_exploration": SEARCH_EXPLORATION,
            "mccfr_iterations": MCCFR_ITERATIONS,
        },
        "runtime_seconds": {"search": search_seconds, "mccfr": mccfr_seconds},
        "native_profiles": {
            "search_information_states": len(search),
            "mccfr_information_states": len(mccfr),
            "search_profile_sha256": _profile_sha256(search),
            "mccfr_profile_sha256": _profile_sha256(mccfr),
            "mccfr_terminal_evaluations": mccfr_snapshot.terminal_evaluations,
        },
        "validation": {"search": search_validation, "mccfr": mccfr_validation},
        "overlap": overlap,
        "shared_native_diagnostics": _shared_diagnostics(search, mccfr),
        "maps": {
            "S_search_native_only": s_accounting,
            "M_mccfr_native_only": m_accounting,
            "H_search_priority_hybrid": h_accounting,
        },
        "hybrid_native_preservation": preservation,
        "seed_pass": all((
            validation_pass,
            arithmetic_pass,
            source_semantics_pass,
            preservation["search_native_preserved_exactly"],
            preservation["mccfr_backfill_preserved_exactly"],
            preservation["mccfr_never_overwrites_search"],
            h_accounting["counts"][MISSING] > 0,
        )),
    }


def run() -> dict:
    if MCCFR_ITERATIONS not in Q0D_TESTED_BUDGETS:
        raise RuntimeError("Q1A MCCFR budget is not part of the precommitted Q0D tested ladder")

    worlds = broad_worlds()
    base_state = public_pre_r3_state()
    validate_broad_physical_support(base_state, worlds)
    support_rows = build_reachable_support(base_state, worlds)
    support_by_key, nonroot_keys, ambiguous_nonroot_keys, root_keys = _support_maps(support_rows)
    if len(worlds) != 36 or len(root_keys) != 3:
        raise RuntimeError("05G frozen support geometry changed")

    seed_results = [
        _run_seed(
            seed=seed,
            base_state=base_state,
            worlds=worlds,
            support_rows=support_rows,
            support_by_key=support_by_key,
        )
        for seed in SEEDS
    ]

    quality = {
        "support_36_worlds": len(worlds) == 36,
        "exhaustive_support_nonempty": len(support_rows) > 0,
        "q0d_selected_budget_is_precommitted_1024": MCCFR_ITERATIONS == 1024 and MCCFR_ITERATIONS in Q0D_TESTED_BUDGETS,
        "both_seeds_pass": len(seed_results) == 2 and all(row["seed_pass"] for row in seed_results),
        "seeds_kept_separate": [row["seed"] for row in seed_results] == list(SEEDS),
        "no_completion_used": True,
        "no_exact_profile_ev_used": True,
        "no_best_response_used": True,
        "no_strength_winner_claim": True,
    }
    passed = all(quality.values())

    source_paths = [
        "tools/openofc_solver/EXTERNAL_05G_BROAD_HIDDEN_INFORMATION_CONTRACT.md",
        "tools/openofc_solver/EXTERNAL_05G_Q0D_MCCFR_COVERAGE_SCALING_CONTRACT.md",
        "tools/openofc_solver/EXTERNAL_05G_Q1A_NATIVE_PROVENANCE_ROUTER_CONTRACT.md",
        "tools/openofc_solver/external_05g_broad_support.py",
        "tools/openofc_solver/external_hidden_discard_overlap.py",
        "tools/openofc_solver/external_hidden_discard_overlap_strategic.py",
        "tools/openofc_solver/run_external_05g_q0b.py",
        "tools/openofc_solver/run_external_05g_q0d.py",
        "tools/openofc_solver/run_external_05g_q1a.py",
    ]
    payload = {
        "schema": "openofc-external-component-ab-v1",
        "experiment_id": EXPERIMENT_ID,
        "authority": AUTHORITY,
        "component": "native-provenance-router-no-strategic-evaluation",
        "config": {
            "seeds": list(SEEDS),
            "search_iterations": SEARCH_ITERATIONS,
            "search_exploration": SEARCH_EXPLORATION,
            "mccfr_iterations": MCCFR_ITERATIONS,
            "q0d_selection_reason": Q0D_SELECTION_REASON,
            "q0d_tested_budgets": list(Q0D_TESTED_BUDGETS),
            "support_worlds": len(worlds),
            "support_sha256": support_sha256(worlds),
        },
        "exhaustive_support": {
            "reachable_information_states": len(support_rows),
            "nonroot_information_states": len(nonroot_keys),
            "ambiguous_nonroot_information_states": len(ambiguous_nonroot_keys),
            "root_information_states": len(root_keys),
        },
        "seed_results": seed_results,
        "quality": quality,
        "verdict": "PASS_NATIVE_PROVENANCE" if passed else "BLOCK_NATIVE_PROVENANCE",
        "promotion_recommendation": "CONTINUE_TO_Q1B_EXPLICIT_COMPLETION" if passed else "FIX_Q1A_TECHNICAL_DEFECT_WITHOUT_MOVING_FROZEN_BUDGETS",
        "limitations": [
            "native coverage and Search/MCCFR disagreement are diagnostics, not strategic ranking",
            "MISSING information states are intentionally not completed in Q1A",
            "finite reduced 36-world game only",
            "no REAL route is certified",
        ],
        "files": [
            {"path": path, "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}
            for path in source_paths
        ],
        "real_routes_certified": 0,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    payload["sha256"] = hashlib.sha256(raw).hexdigest()
    if not passed:
        raise RuntimeError(f"05G-Q1A failed: {quality}")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/external_05g_q1a.json")
    args = parser.parse_args()
    payload = run()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "experiment_id": payload["experiment_id"],
        "verdict": payload["verdict"],
        "seed_summaries": [
            {
                "seed": row["seed"],
                "search_native": row["native_profiles"]["search_information_states"],
                "mccfr_native": row["native_profiles"]["mccfr_information_states"],
                "hybrid_missing": row["maps"]["H_search_priority_hybrid"]["counts"][MISSING],
                "shared_native": row["overlap"]["search_intersection_mccfr"],
                "mean_shared_tv": row["shared_native_diagnostics"]["mean_tv"],
            }
            for row in payload["seed_results"]
        ],
        "manifest_sha256": payload["sha256"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
