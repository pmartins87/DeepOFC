from __future__ import annotations

"""Run 05F-Q3 reach-weighted Search completion against the frozen Q1 baseline."""

import argparse
import hashlib
import json
import math
from pathlib import Path

from external_hidden_discard_overlap import run_overlap_infoset_uct
from external_hidden_discard_overlap_reach_audit import audit_overlap_conditional_reach, summarize_overlap_reach
from external_hidden_discard_overlap_strategic import (
    OverlapExternalSamplingMCCFR,
    build_reachable_support,
    complete_profile,
    exact_nash_conv,
    exact_profile_value,
    visit_profile_from_overlap_search,
)
from external_hidden_discard_reach_completion import (
    AUTHORITY,
    build_counterfactual_priors,
    complete_with_counterfactual_priors,
)
from test_external_hidden_discard_overlap import _overlap_worlds, _public_pre_r3_state

EXPERIMENT_ID = "EXT-05F-Q3-REACH-WEIGHTED-SEARCH-COMPLETION"
UCT_ITERATIONS = 6_000
UCT_SEED = 2026082891
UCT_EXPLORATION = 1.25
MCCFR_ITERATIONS = 512
MCCFR_SEED = 2026082903
COMPLETION_MIN_ITERATIONS = 64
SEARCH_Q1_COMPLETION_SEED = 2026082909
MCCFR_Q1_COMPLETION_SEED = 2026082917
SEARCH_Q3_COMPLETION_SEED = 2026082929
Q1_RUN_ID = 33169170540
Q2_RUN_ID = 33169478995
Q1_SEARCH_EXPLOITABILITY = 0.09209047925455316
Q1_MCCFR_EXPLOITABILITY = 7.105427357601002e-15


def _profile_sha(profile) -> str:
    raw = json.dumps(profile, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def _merge_by_actor(rows, p0_profile, p1_profile):
    merged = {}
    for row in rows:
        source = p0_profile if row.actor == 0 else p1_profile
        merged[row.information_state_key] = dict(source[row.information_state_key])
    return merged


def _distribution_l1(a, b) -> float:
    keys = set(a) | set(b)
    return sum(abs(float(a.get(key, 0.0)) - float(b.get(key, 0.0))) for key in keys)


def _prior_summary(priors, missing_keys):
    relevant = [prior for prior in priors if prior.information_state_key in missing_keys]
    positive = [prior for prior in relevant if not prior.zero_counterfactual_mass]
    nonuniform = [prior for prior in positive if prior.uniform_tv is not None and prior.uniform_tv > 1e-12]
    tvs = sorted(float(prior.uniform_tv) for prior in positive if prior.uniform_tv is not None)
    return {
        "missing_infosets": len(relevant),
        "positive_counterfactual_infosets": len(positive),
        "zero_counterfactual_infosets": len(relevant) - len(positive),
        "nonuniform_positive_infosets": len(nonuniform),
        "uniform_tv_mean": (sum(tvs) / len(tvs)) if tvs else None,
        "uniform_tv_max": max(tvs) if tvs else None,
    }


def run() -> dict:
    worlds = _overlap_worlds()
    state = _public_pre_r3_state()
    rows = build_reachable_support(state, worlds)
    max_actions = max(len(row.action_keys) for row in rows)
    completion_iterations = max(COMPLETION_MIN_ITERATIONS, max_actions)

    search = run_overlap_infoset_uct(
        state,
        worlds,
        iterations=UCT_ITERATIONS,
        seed=UCT_SEED,
        exploration=UCT_EXPLORATION,
    )
    search_base = visit_profile_from_overlap_search(search)
    search_missing = {row.information_state_key for row in rows} - set(search_base)

    mccfr = OverlapExternalSamplingMCCFR(state, worlds, seed=MCCFR_SEED)
    mccfr.run(MCCFR_ITERATIONS)
    mccfr_base = mccfr.current_profile()

    # Reproduce Q1 exactly. This complete Search profile is frozen as the belief
    # and rollout reference for the one-pass Q3 variant.
    search_q1 = complete_profile(
        search_base,
        rows,
        iterations_per_missing_infoset=completion_iterations,
        seed=SEARCH_Q1_COMPLETION_SEED,
        exploration=1.0,
    )
    mccfr_q1 = complete_profile(
        mccfr_base,
        rows,
        iterations_per_missing_infoset=completion_iterations,
        seed=MCCFR_Q1_COMPLETION_SEED,
        exploration=1.0,
    )
    search_q1_nash = exact_nash_conv(state, worlds, profile=search_q1.profile, support_rows=rows)
    mccfr_q1_nash = exact_nash_conv(state, worlds, profile=mccfr_q1.profile, support_rows=rows)
    if not math.isclose(search_q1_nash.exploitability, Q1_SEARCH_EXPLOITABILITY, rel_tol=0.0, abs_tol=1e-10):
        raise RuntimeError("Q3 failed to reproduce frozen Q1 Search exploitability")
    if not math.isclose(mccfr_q1_nash.exploitability, Q1_MCCFR_EXPLOITABILITY, rel_tol=0.0, abs_tol=1e-10):
        raise RuntimeError("Q3 failed to reproduce frozen Q1 MCCFR exploitability")

    priors = build_counterfactual_priors(
        state,
        worlds,
        support_rows=rows,
        reference_profile=search_q1.profile,
    )
    search_q3 = complete_with_counterfactual_priors(
        search_base,
        rows,
        reference_profile=search_q1.profile,
        priors=priors,
        iterations_per_resolved_infoset=completion_iterations,
        seed=SEARCH_Q3_COMPLETION_SEED,
        exploration=1.0,
    )

    # Original Search decisions are a frozen causal surface and must be exactly
    # preserved. Only Q1-synthetic missing decisions may change in Q3.
    for key, distribution in search_base.items():
        if search_q3.profile[key] != distribution:
            raise RuntimeError("Q3 changed an original UCT-covered information state")

    changed_missing = sum(
        1
        for key in search_missing
        if _distribution_l1(search_q1.profile[key], search_q3.profile[key]) > 1e-12
    )
    max_missing_l1 = max(
        (_distribution_l1(search_q1.profile[key], search_q3.profile[key]) for key in search_missing),
        default=0.0,
    )

    search_q3_nash = exact_nash_conv(state, worlds, profile=search_q3.profile, support_rows=rows)
    search_q1_self = exact_profile_value(state, worlds, profile=search_q1.profile, support_rows=rows)
    search_q3_self = exact_profile_value(state, worlds, profile=search_q3.profile, support_rows=rows)
    q1_p0_vs_mccfr = exact_profile_value(
        state,
        worlds,
        profile=_merge_by_actor(rows, search_q1.profile, mccfr_q1.profile),
        support_rows=rows,
    )
    q3_p0_vs_mccfr = exact_profile_value(
        state,
        worlds,
        profile=_merge_by_actor(rows, search_q3.profile, mccfr_q1.profile),
        support_rows=rows,
    )
    mccfr_p0_vs_q1 = exact_profile_value(
        state,
        worlds,
        profile=_merge_by_actor(rows, mccfr_q1.profile, search_q1.profile),
        support_rows=rows,
    )
    mccfr_p0_vs_q3 = exact_profile_value(
        state,
        worlds,
        profile=_merge_by_actor(rows, mccfr_q1.profile, search_q3.profile),
        support_rows=rows,
    )

    # Fresh audit of the resulting Q3 profile. These are post-update diagnostics,
    # not the frozen priors used to construct Q3.
    q3_audit = audit_overlap_conditional_reach(
        state, worlds, support_rows=rows, profile=search_q3.profile
    )
    q3_reach_summary = summarize_overlap_reach(q3_audit)
    prior_summary = _prior_summary(priors, search_missing)

    source_paths = [
        "tools/openofc_solver/external_hidden_discard_overlap.py",
        "tools/openofc_solver/external_hidden_discard_overlap_strategic.py",
        "tools/openofc_solver/external_hidden_discard_overlap_reach_audit.py",
        "tools/openofc_solver/external_hidden_discard_reach_completion.py",
        "tools/openofc_solver/test_external_hidden_discard_reach_completion.py",
        "tools/openofc_solver/run_external_05f_q3.py",
        "tools/openofc_solver/EXTERNAL_05F_Q3_REACH_WEIGHTED_COMPLETION_CONTRACT.md",
    ]
    q1_exploit = search_q1_nash.exploitability
    q3_exploit = search_q3_nash.exploitability
    payload = {
        "schema": "openofc-external-component-ab-v1",
        "experiment_id": EXPERIMENT_ID,
        "authority": AUTHORITY,
        "component": "q1-uniform-vs-q3-counterfactual-reach-weighted-search-completion",
        "q1_reference_run_id": Q1_RUN_ID,
        "q2_trigger_run_id": Q2_RUN_ID,
        "fixed_game": {
            "support_worlds": len(worlds),
            "reachable_information_states": len(rows),
            "search_original_information_states": len(search_base),
            "search_missing_information_states": len(search_missing),
            "max_legal_actions": max_actions,
        },
        "frozen_q1_reproduction": {
            "search_profile_sha256": _profile_sha(search_q1.profile),
            "search_exploitability": q1_exploit,
            "mccfr_profile_sha256": _profile_sha(mccfr_q1.profile),
            "mccfr_exploitability": mccfr_q1_nash.exploitability,
        },
        "counterfactual_prior": prior_summary,
        "q3_completion": {
            "profile_sha256": _profile_sha(search_q3.profile),
            "changed_missing_information_states": changed_missing,
            "changed_missing_fraction": changed_missing / len(search_missing) if search_missing else 0.0,
            "max_missing_policy_l1": max_missing_l1,
            "positive_counterfactual_resolutions": search_q3.positive_counterfactual_resolutions,
            "zero_counterfactual_fallback_resolutions": search_q3.zero_counterfactual_fallback_resolutions,
            "iterations_per_resolved_infoset": completion_iterations,
            "seed": SEARCH_Q3_COMPLETION_SEED,
        },
        "exact_ab": {
            "q1_search": {
                "self_u0": search_q1_self.expected_u0,
                "br0": search_q1_nash.br0.value,
                "br1": search_q1_nash.br1.value,
                "nash_conv": search_q1_nash.nash_conv,
                "exploitability": q1_exploit,
            },
            "q3_search": {
                "self_u0": search_q3_self.expected_u0,
                "br0": search_q3_nash.br0.value,
                "br1": search_q3_nash.br1.value,
                "nash_conv": search_q3_nash.nash_conv,
                "exploitability": q3_exploit,
            },
            "mccfr_control_exploitability": mccfr_q1_nash.exploitability,
            "q1_search_p0_vs_mccfr_p1": q1_p0_vs_mccfr.expected_u0,
            "q3_search_p0_vs_mccfr_p1": q3_p0_vs_mccfr.expected_u0,
            "mccfr_p0_vs_q1_search_p1": mccfr_p0_vs_q1.expected_u0,
            "mccfr_p0_vs_q3_search_p1": mccfr_p0_vs_q3.expected_u0,
            "q3_minus_q1_exploitability": q3_exploit - q1_exploit,
        },
        "q3_post_update_reach_audit": q3_reach_summary,
        "decision": {
            "q3_exactly_improves_exploitability": q3_exploit < q1_exploit - 1e-12,
            "q3_ties_exploitability": math.isclose(q3_exploit, q1_exploit, rel_tol=0.0, abs_tol=1e-12),
            "recommendation": (
                "PREFER_Q3_REACH_WEIGHTED_SEARCH_ON_THIS_FIXTURE"
                if q3_exploit < q1_exploit - 1e-12
                else "KEEP_Q1_UNIFORM_SEARCH_ON_THIS_FIXTURE"
            ),
            "self_consistency_claimed": False,
            "production_promotion_allowed": False,
        },
        "quality": {
            "frozen_q1_reproduced": True,
            "original_search_surface_preserved": True,
            "q3_profile_complete": len(search_q3.profile) == len(rows),
            "exact_metrics_finite": all(math.isfinite(value) for value in [q1_exploit, q3_exploit, search_q3_self.expected_u0]),
            "no_certification_claim": True,
        },
        "files": [
            {"path": path, "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}
            for path in source_paths
        ],
        "limitations": [
            "four-world deliberately constructed reduced support",
            "Q3 is a one-pass update anchored to the frozen Q1 completed profile",
            "zero-counterfactual-reach missing infosets use declared uniform hidden-state fallback",
            "post-Q3 counterfactual beliefs may differ from the frozen priors used to build Q3",
            "no real Bellman route certification",
        ],
        "real_routes_certified": 0,
    }
    if not all(payload["quality"].values()):
        raise RuntimeError(f"05F-Q3 quality gate failed: {payload['quality']}")
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    payload["sha256"] = hashlib.sha256(raw).hexdigest()
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/external_05f_q3.json")
    args = parser.parse_args()
    payload = run()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "experiment_id": payload["experiment_id"],
        "q1_exploitability": payload["exact_ab"]["q1_search"]["exploitability"],
        "q3_exploitability": payload["exact_ab"]["q3_search"]["exploitability"],
        "delta_exploitability": payload["exact_ab"]["q3_minus_q1_exploitability"],
        "changed_missing_information_states": payload["q3_completion"]["changed_missing_information_states"],
        "zero_cf_fallbacks": payload["q3_completion"]["zero_counterfactual_fallback_resolutions"],
        "post_q3_uniform_vs_cf": payload["q3_post_update_reach_audit"]["uniform_vs_counterfactual_tv"],
        "recommendation": payload["decision"]["recommendation"],
        "manifest_sha256": payload["sha256"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
