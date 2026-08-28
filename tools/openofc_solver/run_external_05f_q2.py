from __future__ import annotations

"""Run 05F-Q2 conditional reach audit on the frozen Q1 completed profiles."""

import argparse
import hashlib
import json
import math
from pathlib import Path

from external_hidden_discard_overlap import run_overlap_infoset_uct
from external_hidden_discard_overlap_reach_audit import (
    AUTHORITY,
    audit_overlap_conditional_reach,
    summarize_overlap_reach,
)
from external_hidden_discard_overlap_strategic import (
    OverlapExternalSamplingMCCFR,
    build_reachable_support,
    complete_profile,
    visit_profile_from_overlap_search,
)
from test_external_hidden_discard_overlap import _overlap_worlds, _public_pre_r3_state

EXPERIMENT_ID = "EXT-05F-Q2-HIDDEN-DISCARD-CONDITIONAL-REACH"
UCT_ITERATIONS = 6_000
UCT_SEED = 2026082891
UCT_EXPLORATION = 1.25
MCCFR_ITERATIONS = 512
MCCFR_SEED = 2026082903
COMPLETION_MIN_ITERATIONS = 64
SEARCH_COMPLETION_SEED = 2026082909
MCCFR_COMPLETION_SEED = 2026082917
Q1_RUN_ID = 33169170540


def _top_ambiguous(audit, limit: int = 12):
    rows = [
        row for row in audit.rows
        if row.compatible_states > 1 and row.uniform_vs_counterfactual_tv is not None
    ]
    rows.sort(
        key=lambda row: (
            float(row.uniform_vs_counterfactual_tv),
            row.compatible_states,
            row.information_state_key,
        ),
        reverse=True,
    )
    return [
        {
            "infoset_sha256": hashlib.sha256(row.information_state_key.encode()).hexdigest(),
            "round": row.round_index,
            "actor": row.actor,
            "compatible_states": row.compatible_states,
            "positive_counterfactual_states": row.positive_counterfactual_states,
            "uniform_vs_counterfactual_tv": row.uniform_vs_counterfactual_tv,
            "uniform_vs_full_tv": row.uniform_vs_full_tv,
            "full_vs_counterfactual_tv": row.full_vs_counterfactual_tv,
            "counterfactual_effective_support": row.counterfactual_effective_support,
        }
        for row in rows[:limit]
    ]


def _valid_audit(audit) -> bool:
    for row in audit.rows:
        for value in (row.uniform_vs_full_tv, row.uniform_vs_counterfactual_tv, row.full_vs_counterfactual_tv):
            if value is not None and (not math.isfinite(value) or not 0.0 <= value <= 1.0):
                return False
    return True


def run() -> dict:
    worlds = _overlap_worlds()
    state = _public_pre_r3_state()
    rows = build_reachable_support(state, worlds)
    max_actions = max(len(row.action_keys) for row in rows)
    completion_iterations = max(COMPLETION_MIN_ITERATIONS, max_actions)

    search = run_overlap_infoset_uct(
        state, worlds, iterations=UCT_ITERATIONS, seed=UCT_SEED, exploration=UCT_EXPLORATION
    )
    search_base = visit_profile_from_overlap_search(search)
    mccfr = OverlapExternalSamplingMCCFR(state, worlds, seed=MCCFR_SEED)
    mccfr.run(MCCFR_ITERATIONS)
    mccfr_base = mccfr.current_profile()

    search_profile = complete_profile(
        search_base,
        rows,
        iterations_per_missing_infoset=completion_iterations,
        seed=SEARCH_COMPLETION_SEED,
        exploration=1.0,
    ).profile
    mccfr_profile = complete_profile(
        mccfr_base,
        rows,
        iterations_per_missing_infoset=completion_iterations,
        seed=MCCFR_COMPLETION_SEED,
        exploration=1.0,
    ).profile

    search_audit = audit_overlap_conditional_reach(
        state, worlds, support_rows=rows, profile=search_profile
    )
    mccfr_audit = audit_overlap_conditional_reach(
        state, worlds, support_rows=rows, profile=mccfr_profile
    )
    search_summary = summarize_overlap_reach(search_audit)
    mccfr_summary = summarize_overlap_reach(mccfr_audit)

    search_max = search_summary["uniform_vs_counterfactual_tv"]["max"]
    mccfr_max = mccfr_summary["uniform_vs_counterfactual_tv"]["max"]
    source_paths = [
        "tools/openofc_solver/external_hidden_discard_overlap.py",
        "tools/openofc_solver/external_hidden_discard_overlap_strategic.py",
        "tools/openofc_solver/external_hidden_discard_overlap_reach_audit.py",
        "tools/openofc_solver/test_external_hidden_discard_overlap_reach_audit.py",
        "tools/openofc_solver/run_external_05f_q2.py",
        "tools/openofc_solver/EXTERNAL_05F_HIDDEN_DISCARD_OVERLAP_CONTRACT.md",
    ]
    payload = {
        "schema": "openofc-external-component-ab-v1",
        "experiment_id": EXPERIMENT_ID,
        "authority": AUTHORITY,
        "component": "hidden-discard-overlap-conditional-reach-audit",
        "q1_reference_run_id": Q1_RUN_ID,
        "fixed_game": {
            "support_worlds": len(worlds),
            "reachable_information_states": len(rows),
            "ambiguous_information_states": sum(1 for row in rows if len(row.concrete_states) > 1),
            "completion_iterations_per_missing_infoset": completion_iterations,
        },
        "search": {
            "summary": search_summary,
            "top_ambiguous_counterfactual_tv": _top_ambiguous(search_audit),
        },
        "mccfr": {
            "summary": mccfr_summary,
            "top_ambiguous_counterfactual_tv": _top_ambiguous(mccfr_audit),
        },
        "interpretation_gate": {
            "search_uniform_prior_exact_on_all_defined_ambiguous_infosets": search_max is not None and search_max <= 1e-12,
            "mccfr_uniform_prior_exact_on_all_defined_ambiguous_infosets": mccfr_max is not None and mccfr_max <= 1e-12,
            "if_false": "Q1 local completion uses a measurably wrong hidden-state weighting on at least one ambiguous infoset; implement reach-weighted completion before architecture ranking.",
        },
        "quality": {
            "search_audit_valid": _valid_audit(search_audit),
            "mccfr_audit_valid": _valid_audit(mccfr_audit),
            "ambiguous_support_exercised": search_audit.ambiguous_information_states > 1 and mccfr_audit.ambiguous_information_states > 1,
            "no_certification_claim": True,
        },
        "files": [
            {"path": path, "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}
            for path in source_paths
        ],
        "limitations": [
            "four-world deliberately constructed reduced support",
            "audit measures the finite Q1 completed policies, not the full production game",
            "Q2 is diagnostic; nonzero TV does not itself rank Search versus MCCFR",
            "no real Bellman route certification",
        ],
        "promotion_recommendation": "USE_Q2_TO_DECIDE_IF_05F_Q3_REACH_WEIGHTED_COMPLETION_IS_REQUIRED",
        "real_routes_certified": 0,
    }
    if not all(payload["quality"].values()):
        raise RuntimeError(f"05F-Q2 gate failed: {payload['quality']}")
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    payload["sha256"] = hashlib.sha256(raw).hexdigest()
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/external_05f_q2.json")
    args = parser.parse_args()
    payload = run()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "experiment_id": payload["experiment_id"],
        "search_uniform_vs_cf": payload["search"]["summary"]["uniform_vs_counterfactual_tv"],
        "mccfr_uniform_vs_cf": payload["mccfr"]["summary"]["uniform_vs_counterfactual_tv"],
        "search_uniform_prior_exact": payload["interpretation_gate"]["search_uniform_prior_exact_on_all_defined_ambiguous_infosets"],
        "mccfr_uniform_prior_exact": payload["interpretation_gate"]["mccfr_uniform_prior_exact_on_all_defined_ambiguous_infosets"],
        "manifest_sha256": payload["sha256"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
