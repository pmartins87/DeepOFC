from __future__ import annotations

"""Run the 05D-Q0 independent MCCFR-vs-UCT comparator smoke."""

import argparse
import hashlib
import json
import math
from pathlib import Path

from external_two_street_infoset_search import run_two_street_infoset_uct
from external_two_street_mccfr import (
    AUTHORITY,
    TwoStreetExternalSamplingMCCFR,
    exact_profile_value,
    root_total_variation,
    visit_profile_from_search,
)
from strategic_cfr import information_state_key, legal_action_pairs
from test_external_two_street_infoset_search import _coherent_r3_state, _support_worlds

EXPERIMENT_ID = "EXT-05D-Q0-MCCFR-VS-UCT"
UCT_ITERATIONS = 5_000
UCT_SEED = 2026082831
MCCFR_ITERATIONS = 256
MCCFR_SEED = 2026082853


def _root_distribution(state, profile):
    key = information_state_key(state)
    action_keys = tuple(action_key for action_key, _action in legal_action_pairs(state))
    supplied = profile.get(key, {})
    weights = {action_key: float(supplied.get(action_key, 0.0)) for action_key in action_keys}
    mass = sum(weights.values())
    if mass <= 0.0:
        return {action_key: 1.0 / len(action_keys) for action_key in action_keys}
    return {action_key: value / mass for action_key, value in weights.items()}


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
    search_profile = visit_profile_from_search(search)

    trainer = TwoStreetExternalSamplingMCCFR(state, worlds, seed=MCCFR_SEED)
    trainer.run(MCCFR_ITERATIONS)
    cfr_profile = trainer.current_profile()
    cfr_snapshot = trainer.snapshot()

    evaluations = {
        "search_self": exact_profile_value(
            state, worlds, p0_profile=search_profile, p1_profile=search_profile
        ),
        "mccfr_self": exact_profile_value(
            state, worlds, p0_profile=cfr_profile, p1_profile=cfr_profile
        ),
        "search_p0_vs_mccfr_p1": exact_profile_value(
            state, worlds, p0_profile=search_profile, p1_profile=cfr_profile
        ),
        "mccfr_p0_vs_search_p1": exact_profile_value(
            state, worlds, p0_profile=cfr_profile, p1_profile=search_profile
        ),
    }
    root_tv = root_total_variation(state, search_profile, cfr_profile)
    search_root = _root_distribution(state, search_profile)
    cfr_root = _root_distribution(state, cfr_profile)

    source_paths = [
        "tools/openofc_solver/external_two_street_infoset_search.py",
        "tools/openofc_solver/external_two_street_mccfr.py",
        "tools/openofc_solver/test_external_two_street_mccfr.py",
        "tools/openofc_solver/run_external_two_street_05d_q0.py",
        "tools/openofc_solver/strategic_cfr.py",
    ]
    payload = {
        "schema": "openofc-external-component-ab-v1",
        "experiment_id": EXPERIMENT_ID,
        "authority": AUTHORITY,
        "component": "reduced-two-street-mccfr-vs-uct",
        "fixed_game": {
            "support_worlds": len(worlds),
            "uniform_chance": True,
            "canonical_terminal_utility": True,
            "canonical_infoset_keys": True,
        },
        "uct": {
            "iterations": UCT_ITERATIONS,
            "seed": UCT_SEED,
            "selected_root_action_key": search.selected_root_action_key,
            "infoset_count": search.infoset_count,
            "profile_extraction": "local_action_visit_frequencies_with_uniform_unseen_infoset_fallback",
            "root_distribution": search_root,
        },
        "mccfr": {
            "iterations": MCCFR_ITERATIONS,
            "seed": MCCFR_SEED,
            "information_states": cfr_snapshot.information_states,
            "training_terminal_evaluations": cfr_snapshot.terminal_evaluations,
            "profile_kind": "current_regret_matching",
            "reach_weighted_average_implemented": False,
            "root_distribution": cfr_root,
        },
        "comparison": {
            name: {
                "expected_u0": result.expected_u0,
                "terminal_leaves": result.terminal_leaves,
                "information_states_seen": result.information_states_seen,
            }
            for name, result in evaluations.items()
        },
        "root_total_variation": root_tv,
        "quality": {
            "all_fixed_profile_values_finite": all(
                math.isfinite(result.expected_u0) for result in evaluations.values()
            ),
            "root_total_variation_valid": 0.0 <= root_tv <= 1.0,
            "mccfr_profile_nonempty": bool(cfr_profile),
            "same_root_information_state": cfr_snapshot.root_information_state_key == information_state_key(state),
            "no_equilibrium_claim": True,
            "no_exploitability_claim": True,
        },
        "files": [
            {"path": path, "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}
            for path in source_paths
        ],
        "limitations": [
            "six-world reduced support",
            "MCCFR Q0 uses current regret-matching profile only",
            "search profile uses visit frequencies with uniform fallback for unseen infosets",
            "no best-response or exploitability authority",
            "not a posterior conditioned on earlier-round strategic signalling",
        ],
        "promotion_recommendation": "CONTINUE_TO_05D_Q1_BUDGETED_COMPARATOR",
        "real_routes_certified": 0,
    }
    if not all(payload["quality"].values()):
        raise RuntimeError(f"05D-Q0 mechanical comparator gate failed: {payload['quality']}")
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["sha256"] = hashlib.sha256(raw).hexdigest()
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/external_two_street_05d_q0.json")
    args = parser.parse_args()
    payload = run()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "experiment_id": payload["experiment_id"],
        "root_total_variation": payload["root_total_variation"],
        "comparison": {
            name: values["expected_u0"] for name, values in payload["comparison"].items()
        },
        "mccfr_information_states": payload["mccfr"]["information_states"],
        "manifest_sha256": payload["sha256"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
