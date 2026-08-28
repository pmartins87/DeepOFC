from __future__ import annotations

"""Run the frozen 05C-Q1 multi-budget/multi-seed reproducibility matrix."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from statistics import mean, pstdev

from external_two_street_infoset_search import AUTHORITY, run_two_street_infoset_uct
from test_external_two_street_infoset_search import _coherent_r3_state, _support_worlds

BUDGETS = (1_000, 5_000, 20_000)
SEEDS = (2026082841, 2026082843, 2026082847, 2026082849)
EXPLORATION = 1.0
EXPERIMENT_ID = "EXT-ISMCTS-05C-Q1-REPRODUCIBILITY"
BASELINE_SHA = "c3430819d6cb22c8ad823791a35374d56a88a32a"
Q0_RUN = 33141837728
Q0_MANIFEST_SHA256 = "293a09972103505cc6b17555a4a57c9273c9750e9688c83db6d631d1bbca93be"


def _selected_root(result):
    return next(
        stat for stat in result.root_action_stats
        if stat.action_key == result.selected_root_action_key
    )


def _row(result, budget: int, seed: int) -> dict:
    layers = {(s.round_index, s.actor) for s in result.layer_stats}
    expected_layers = {(3, 0), (3, 1), (4, 0), (4, 1)}
    selected = _selected_root(result)
    root_visit_total = sum(stat.visits for stat in result.root_action_stats)
    quality = {
        "authority_matches": result.authority == AUTHORITY,
        "support_worlds_match": result.support_worlds == 6,
        "all_four_layers_reached": layers == expected_layers,
        "terminal_episode_count_matches": result.terminal_episodes == budget,
        "root_visit_total_matches": root_visit_total == budget,
        "coverage_count_valid": result.fully_explored_infosets <= result.infoset_count,
    }
    if not all(quality.values()):
        raise RuntimeError(f"mechanical Q1 cell failure budget={budget} seed={seed}: {quality}")
    return {
        "budget": budget,
        "seed": seed,
        "selected_root_action_key": result.selected_root_action_key,
        "selected_root_visits": selected.visits,
        "selected_root_visit_share": selected.visits / budget,
        "selected_root_mean": selected.mean_value,
        "infoset_count": result.infoset_count,
        "fully_explored_infosets": result.fully_explored_infosets,
        "fully_explored_fraction": result.fully_explored_infosets / result.infoset_count,
        "terminal_mean_p0_utility": result.terminal_mean_p0_utility,
        "terminal_min_p0_utility": result.terminal_min_p0_utility,
        "terminal_max_p0_utility": result.terminal_max_p0_utility,
        "layer_stats": [
            {
                "round": s.round_index,
                "actor": s.actor,
                "infosets": s.infosets,
                "total_visits": s.total_visits,
            }
            for s in result.layer_stats
        ],
        "quality": quality,
    }


def _summarize(rows: list[dict], budget: int) -> dict:
    subset = [row for row in rows if row["budget"] == budget]
    if len(subset) != len(SEEDS):
        raise RuntimeError(f"budget {budget} does not contain all frozen seeds")
    counts = Counter(row["selected_root_action_key"] for row in subset)
    dominant_action, dominant_count = sorted(
        counts.items(), key=lambda item: (-item[1], item[0])
    )[0]
    terminal_means = [row["terminal_mean_p0_utility"] for row in subset]
    infosets = [row["infoset_count"] for row in subset]
    return {
        "budget": budget,
        "selected_action_counts": dict(sorted(counts.items())),
        "unique_selected_actions": len(counts),
        "dominant_action_key": dominant_action,
        "dominant_action_count": dominant_count,
        "dominant_action_fraction": dominant_count / len(subset),
        "mean_selected_root_visit_share": mean(row["selected_root_visit_share"] for row in subset),
        "terminal_mean_p0_utility_mean": mean(terminal_means),
        "terminal_mean_p0_utility_pstdev": pstdev(terminal_means),
        "infoset_count_min": min(infosets),
        "infoset_count_mean": mean(infosets),
        "infoset_count_max": max(infosets),
        "mean_fully_explored_fraction": mean(row["fully_explored_fraction"] for row in subset),
    }


def run() -> dict:
    worlds = _support_worlds()
    state = _coherent_r3_state(worlds[0])
    rows: list[dict] = []
    for budget in BUDGETS:
        for seed in SEEDS:
            result = run_two_street_infoset_uct(
                state,
                worlds,
                iterations=budget,
                seed=seed,
                exploration=EXPLORATION,
            )
            rows.append(_row(result, budget, seed))

    source_paths = [
        "tools/openofc_solver/external_two_street_infoset_search.py",
        "tools/openofc_solver/test_external_two_street_infoset_search.py",
        "tools/openofc_solver/run_external_two_street_q1.py",
        "tools/openofc_solver/external_research_world_sampler.py",
        "tools/openofc_solver/strategic_cfr.py",
    ]
    payload = {
        "schema": "openofc-external-component-ab-v1",
        "experiment_id": EXPERIMENT_ID,
        "baseline_sha": BASELINE_SHA,
        "q0_reference": {
            "run": Q0_RUN,
            "manifest_sha256": Q0_MANIFEST_SHA256,
        },
        "authority": AUTHORITY,
        "component": "r3-r4-two-street-infoset-reproducibility",
        "matrix": {
            "budgets": list(BUDGETS),
            "seeds": list(SEEDS),
            "exploration": EXPLORATION,
            "support_worlds": len(worlds),
        },
        "files": [
            {"path": path, "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}
            for path in source_paths
        ],
        "rows": rows,
        "budget_summaries": [_summarize(rows, budget) for budget in BUDGETS],
        "interpretation_firewall": {
            "strategic_pass_threshold_defined": False,
            "equilibrium_value_claimed": False,
            "exploitability_claimed": False,
            "certification_claimed": False,
        },
        "promotion_recommendation": "PROCEED_TO_05D_REDUCED_GAME_CFR_COMPARATOR",
        "real_routes_certified": 0,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["sha256"] = hashlib.sha256(raw).hexdigest()
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="artifacts/external_two_street_05c_q1.json",
    )
    args = parser.parse_args()
    payload = run()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "experiment_id": payload["experiment_id"],
        "budget_summaries": payload["budget_summaries"],
        "manifest_sha256": payload["sha256"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
