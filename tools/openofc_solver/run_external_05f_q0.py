from __future__ import annotations

"""Run the 05F-Q0 hidden-discard-overlap mechanics benchmark."""

import argparse
import hashlib
import json
from pathlib import Path

from external_hidden_discard_overlap import (
    AUTHORITY,
    find_hidden_discard_collisions,
    run_overlap_infoset_uct,
)
from test_external_hidden_discard_overlap import _overlap_worlds, _public_pre_r3_state

EXPERIMENT_ID = "EXT-05F-Q0-HIDDEN-DISCARD-OVERLAP"
ITERATIONS = 6_000
SEED = 2026082891
EXPLORATION = 1.25


def _digest_info_key(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def run() -> dict:
    worlds = _overlap_worlds()
    state = _public_pre_r3_state()
    collisions = find_hidden_discard_collisions(state, worlds)
    result = run_overlap_infoset_uct(
        state,
        worlds,
        iterations=ITERATIONS,
        seed=SEED,
        exploration=EXPLORATION,
    )

    layers = {}
    for round_index, actor in sorted({(row.round_index, row.actor) for row in result.node_stats}):
        rows = [row for row in result.node_stats if row.round_index == round_index and row.actor == actor]
        layers[f"R{round_index}_P{actor}"] = {
            "information_states": len(rows),
            "ambiguous_information_states": sum(1 for row in rows if len(row.compatible_worlds) > 1),
            "max_compatible_worlds": max((len(row.compatible_worlds) for row in rows), default=0),
            "visits": sum(row.visits for row in rows),
        }

    witness_payload = [
        {
            "hidden_player": row.hidden_player,
            "observing_player": row.observing_player,
            "round_index_after_action": row.round_index_after_action,
            "world_a": row.world_a,
            "world_b": row.world_b,
            "public_placements": row.public_placements,
            "discarded_a": row.discarded_a,
            "discarded_b": row.discarded_b,
            "observer_infoset_sha256": _digest_info_key(row.observer_information_state_key),
        }
        for row in collisions
    ]
    hidden_players = {row["hidden_player"] for row in witness_payload}

    source_paths = [
        "tools/openofc_solver/external_hidden_discard_overlap.py",
        "tools/openofc_solver/test_external_hidden_discard_overlap.py",
        "tools/openofc_solver/run_external_05f_q0.py",
        "tools/openofc_solver/EXTERNAL_05F_HIDDEN_DISCARD_OVERLAP_CONTRACT.md",
        "tools/openofc_solver/strategic_cfr.py",
    ]
    payload = {
        "schema": "openofc-external-component-ab-v1",
        "experiment_id": EXPERIMENT_ID,
        "authority": AUTHORITY,
        "component": "public-chance-root-hidden-discard-overlap",
        "fixed_game": {
            "support_worlds": len(worlds),
            "p0_private_types": len({tuple(str(card) for card in world.p0_r3) for world in worlds}),
            "p1_private_types": len({tuple(str(card) for card in world.p1_r3) for world in worlds}),
            "canonical_infoset_keys": True,
            "canonical_terminal_utility": True,
            "private_discards": True,
            "single_physical_world_per_episode": True,
        },
        "collision_witnesses": witness_payload,
        "search": {
            "iterations": ITERATIONS,
            "seed": SEED,
            "exploration": EXPLORATION,
            "information_states": result.information_states,
            "ambiguous_information_states": result.ambiguous_information_states,
            "ambiguous_nonroot_information_states": result.ambiguous_nonroot_information_states,
            "max_compatible_worlds": result.max_compatible_worlds,
            "terminal_mean_u0": result.terminal_mean_u0,
            "layers": layers,
        },
        "quality": {
            "p0_hidden_discard_collision_proved": 0 in hidden_players,
            "p1_hidden_discard_collision_proved": 1 in hidden_players,
            "nonroot_ambiguity_observed_by_search": result.ambiguous_nonroot_information_states > 0,
            "at_least_two_private_types_per_player": len({tuple(str(card) for card in world.p0_r3) for world in worlds}) >= 2 and len({tuple(str(card) for card in world.p1_r3) for world in worlds}) >= 2,
            "no_certification_claim": True,
        },
        "files": [
            {"path": path, "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}
            for path in source_paths
        ],
        "limitations": [
            "four-world deliberately constructed reduced support",
            "Q0 validates hidden-discard information overlap and search mechanics only",
            "no MCCFR comparison in Q0",
            "no exact best response or exploitability result in Q0",
            "not a production route",
        ],
        "promotion_recommendation": "CONTINUE_TO_05F_Q1_MCCFR_AND_EXACT_BR_COMPARATOR",
        "real_routes_certified": 0,
    }
    if not all(payload["quality"].values()):
        raise RuntimeError(f"05F-Q0 gate failed: {payload['quality']}")
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    payload["sha256"] = hashlib.sha256(raw).hexdigest()
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/external_05f_q0.json")
    args = parser.parse_args()
    payload = run()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "experiment_id": payload["experiment_id"],
        "collision_witnesses": len(payload["collision_witnesses"]),
        "ambiguous_nonroot_information_states": payload["search"]["ambiguous_nonroot_information_states"],
        "max_compatible_worlds": payload["search"]["max_compatible_worlds"],
        "manifest_sha256": payload["sha256"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
