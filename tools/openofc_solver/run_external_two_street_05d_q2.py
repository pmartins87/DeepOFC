from __future__ import annotations

"""Run 05D-Q2 conditional reach-weight diagnostics on completed profiles."""

import argparse
import hashlib
import json
import math
from pathlib import Path

from external_two_street_counterfactual_resolve import (
    build_reachable_infoset_support,
    complete_profile_with_counterfactual_resolve,
)
from external_two_street_infoset_search import run_two_street_infoset_uct
from external_two_street_mccfr import TwoStreetExternalSamplingMCCFR, visit_profile_from_search
from external_two_street_reach_audit import AUTHORITY, audit_conditional_reach, summarize_reach_audit
from test_external_two_street_infoset_search import _coherent_r3_state, _support_worlds

EXPERIMENT_ID = "EXT-05D-Q2-CONDITIONAL-REACH-AUDIT-V2"
UCT_ITERATIONS = 5_000
UCT_SEED = 2026082831
MCCFR_ITERATIONS = 256
MCCFR_SEED = 2026082853
RESOLVE_MIN_ITERATIONS = 64
SEARCH_RESOLVE_SEED = 2026082871
MCCFR_RESOLVE_SEED = 2026082873
Q1_RUN_ID = 33143759852
Q1_MANIFEST_SHA256 = "f53e94cafd8c3cace5d4e00a4f6e1c6d85bf702a6058b86a6b3a47412ea65e0b"


def _profile_sha256(profile) -> str:
    raw = json.dumps(profile, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _row_digest(info_key: str) -> str:
    return hashlib.sha256(info_key.encode("utf-8")).hexdigest()


def _top_rows(audit, *, field: str, limit: int = 10):
    eligible = [row for row in audit.rows if getattr(row, field) is not None]
    ranked = sorted(
        eligible,
        key=lambda row: (
            float(getattr(row, field)),
            row.compatible_states,
            row.information_state_key,
        ),
        reverse=True,
    )[:limit]
    return [
        {
            "infoset_sha256": _row_digest(row.information_state_key),
            "round": row.round_index,
            "actor": row.actor,
            "compatible_states": row.compatible_states,
            "full_reach_defined": row.full_reach_defined,
            "counterfactual_reach_defined": row.counterfactual_reach_defined,
            "uniform_vs_full_tv": row.uniform_vs_full_tv,
            "uniform_vs_counterfactual_tv": row.uniform_vs_counterfactual_tv,
            "full_vs_counterfactual_tv": row.full_vs_counterfactual_tv,
            "full_effective_support": row.full_effective_support,
            "counterfactual_effective_support": row.counterfactual_effective_support,
        }
        for row in ranked
    ]


def _all_tv_valid(audit) -> bool:
    for row in audit.rows:
        for value in (
            row.uniform_vs_full_tv,
            row.uniform_vs_counterfactual_tv,
            row.full_vs_counterfactual_tv,
        ):
            if value is None:
                continue
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                return False
    return True


def _defined_max(rows, field: str) -> float | None:
    values = [float(getattr(row, field)) for row in rows if getattr(row, field) is not None]
    return max(values) if values else None


def run() -> dict:
    worlds = _support_worlds()
    state = _coherent_r3_state(worlds[0])

    search = run_two_street_infoset_uct(
        state,
        worlds,
        iterations=UCT_ITERATIONS,
        seed=UCT_SEED,
        exploration=1.0,
    )
    search_base = visit_profile_from_search(search)

    trainer = TwoStreetExternalSamplingMCCFR(state, worlds, seed=MCCFR_SEED)
    trainer.run(MCCFR_ITERATIONS)
    mccfr_base = trainer.current_profile()

    reachable = build_reachable_infoset_support(state, worlds)
    max_actions = max(len(row.action_keys) for row in reachable)
    resolve_iterations = max(RESOLVE_MIN_ITERATIONS, max_actions)

    search_completed = complete_profile_with_counterfactual_resolve(
        search_base,
        reachable,
        iterations_per_infoset=resolve_iterations,
        seed=SEARCH_RESOLVE_SEED,
        exploration=1.0,
    )
    mccfr_completed = complete_profile_with_counterfactual_resolve(
        mccfr_base,
        reachable,
        iterations_per_infoset=resolve_iterations,
        seed=MCCFR_RESOLVE_SEED,
        exploration=1.0,
    )

    search_audit = audit_conditional_reach(state, worlds, profile=search_completed.profile)
    mccfr_audit = audit_conditional_reach(state, worlds, profile=mccfr_completed.profile)
    search_summary = summarize_reach_audit(search_audit)
    mccfr_summary = summarize_reach_audit(mccfr_audit)

    search_max_cf_gap = _defined_max(search_audit.rows, "full_vs_counterfactual_tv")
    mccfr_max_cf_gap = _defined_max(mccfr_audit.rows, "full_vs_counterfactual_tv")

    source_paths = [
        "tools/openofc_solver/external_two_street_infoset_search.py",
        "tools/openofc_solver/external_two_street_mccfr.py",
        "tools/openofc_solver/external_two_street_counterfactual_resolve.py",
        "tools/openofc_solver/external_two_street_reach_audit.py",
        "tools/openofc_solver/test_external_two_street_reach_audit.py",
        "tools/openofc_solver/run_external_two_street_05d_q2.py",
        "tools/openofc_solver/EXTERNAL_TWO_STREET_05D_Q2_REACH_WEIGHT_AUDIT_CONTRACT.md",
        "tools/openofc_solver/strategic_cfr.py",
    ]
    payload = {
        "schema": "openofc-external-component-ab-v1",
        "experiment_id": EXPERIMENT_ID,
        "authority": AUTHORITY,
        "component": "conditional-full-and-counterfactual-reach-audit",
        "q1_reference": {
            "run_id": Q1_RUN_ID,
            "manifest_sha256": Q1_MANIFEST_SHA256,
        },
        "fixed_game": {
            "support_worlds": len(worlds),
            "reachable_information_states": len(reachable),
            "max_legal_actions": max_actions,
            "uniform_physical_world_chance": True,
            "canonical_infoset_keys": True,
        },
        "completion": {
            "iterations_per_missing_infoset": resolve_iterations,
            "search_profile_sha256": _profile_sha256(search_completed.profile),
            "mccfr_profile_sha256": _profile_sha256(mccfr_completed.profile),
            "search_completed_information_states": search_completed.completed_information_states,
            "mccfr_completed_information_states": mccfr_completed.completed_information_states,
        },
        "search": {
            "summary": search_summary,
            "top_uniform_vs_counterfactual_tv": _top_rows(
                search_audit, field="uniform_vs_counterfactual_tv"
            ),
            "max_full_vs_counterfactual_tv": search_max_cf_gap,
        },
        "mccfr": {
            "summary": mccfr_summary,
            "top_uniform_vs_counterfactual_tv": _top_rows(
                mccfr_audit, field="uniform_vs_counterfactual_tv"
            ),
            "max_full_vs_counterfactual_tv": mccfr_max_cf_gap,
        },
        "structural_observation": {
            "search_full_and_counterfactual_reach_match_to_1e12_where_both_defined": (
                search_max_cf_gap is not None and search_max_cf_gap <= 1e-12
            ),
            "mccfr_full_and_counterfactual_reach_match_to_1e12_where_both_defined": (
                mccfr_max_cf_gap is not None and mccfr_max_cf_gap <= 1e-12
            ),
            "zero_own_probability_branches_traversed": True,
            "undefined_full_reach_is_not_coerced_to_a_distribution": True,
            "meaning": "full and counterfactual conditional beliefs are separately audited; undefined zero-mass beliefs remain explicit",
        },
        "quality": {
            "search_audit_covers_all_reachable_infosets": search_audit.information_states == len(reachable),
            "mccfr_audit_covers_all_reachable_infosets": mccfr_audit.information_states == len(reachable),
            "search_counterfactual_reach_defined_somewhere": search_audit.counterfactual_reach_defined_information_states > 0,
            "mccfr_counterfactual_reach_defined_somewhere": mccfr_audit.counterfactual_reach_defined_information_states > 0,
            "search_profile_completed_before_audit": search_completed.completed_information_states == len(reachable),
            "mccfr_profile_completed_before_audit": mccfr_completed.completed_information_states == len(reachable),
            "search_tv_metrics_valid": _all_tv_valid(search_audit),
            "mccfr_tv_metrics_valid": _all_tv_valid(mccfr_audit),
            "no_equilibrium_claim": True,
            "no_exploitability_claim": True,
        },
        "files": [
            {"path": path, "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}
            for path in source_paths
        ],
        "limitations": [
            "six-world reduced support",
            "audit conditions on the completed fixed profiles rather than the full earlier-round game",
            "full-reach beliefs are undefined at zero full-reach information states and remain explicitly undefined",
            "counterfactual beliefs are undefined when chance/opponent reach is zero and remain explicitly undefined",
            "uniform-vs-reach TV is diagnostic rather than a certification threshold",
            "no best-response or exploitability authority",
        ],
        "promotion_recommendation": "USE_COUNTERFACTUAL_REACH_TV_TO_DECIDE_WHETHER_05D_Q3_NEEDS_REACH_WEIGHTED_LOCAL_RESOLVER",
        "real_routes_certified": 0,
    }
    if not all(payload["quality"].values()):
        raise RuntimeError(f"05D-Q2 mechanical reach-audit gate failed: {payload['quality']}")
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    payload["sha256"] = hashlib.sha256(raw).hexdigest()
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/external_two_street_05d_q2.json")
    args = parser.parse_args()
    payload = run()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "experiment_id": payload["experiment_id"],
        "search_uniform_vs_counterfactual_tv": payload["search"]["summary"]["uniform_vs_counterfactual_tv"],
        "mccfr_uniform_vs_counterfactual_tv": payload["mccfr"]["summary"]["uniform_vs_counterfactual_tv"],
        "search_max_full_vs_counterfactual_tv": payload["search"]["max_full_vs_counterfactual_tv"],
        "mccfr_max_full_vs_counterfactual_tv": payload["mccfr"]["max_full_vs_counterfactual_tv"],
        "manifest_sha256": payload["sha256"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
