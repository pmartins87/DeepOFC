from __future__ import annotations

"""Run full six-world 05E exact reduced-game BR/NashConv comparison."""

import argparse
import hashlib
import json
import math
from pathlib import Path

from external_two_street_counterfactual_resolve import (
    build_reachable_infoset_support,
    complete_profile_with_counterfactual_resolve,
    exact_profile_value_strict,
)
from external_two_street_exact_br import (
    AUTHORITY,
    exact_nash_conv,
    replay_best_response_value,
)
from external_two_street_infoset_search import run_two_street_infoset_uct
from external_two_street_mccfr import TwoStreetExternalSamplingMCCFR, visit_profile_from_search
from test_external_two_street_infoset_search import _coherent_r3_state, _support_worlds

EXPERIMENT_ID = "EXT-05E-Q0-EXACT-REDUCED-GAME-EXPLOITABILITY"
UCT_ITERATIONS = 5_000
UCT_SEED = 2026082831
MCCFR_ITERATIONS = 256
MCCFR_SEED = 2026082853
RESOLVE_MIN_ITERATIONS = 64
SEARCH_RESOLVE_SEED = 2026082871
MCCFR_RESOLVE_SEED = 2026082873
Q1_MANIFEST_SHA256 = "f53e94cafd8c3cace5d4e00a4f6e1c6d85bf702a6058b86a6b3a47412ea65e0b"
Q1_RUN_ID = 33143759852


def _profile_sha256(profile) -> str:
    raw = json.dumps(profile, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _evaluate_algorithm(state, worlds, support, *, name: str, profile) -> dict:
    self_play = exact_profile_value_strict(
        state,
        worlds,
        support_rows=support,
        p0_profile=profile,
        p1_profile=profile,
    )
    nc = exact_nash_conv(
        state,
        worlds,
        profile=profile,
        support_rows=support,
    )
    replay0 = replay_best_response_value(
        state,
        worlds,
        support_rows=support,
        opponent_profile=profile,
        response=nc.br0,
    )
    replay1 = replay_best_response_value(
        state,
        worlds,
        support_rows=support,
        opponent_profile=profile,
        response=nc.br1,
    )
    replay0_own = replay0.expected_u0
    replay1_own = -replay1.expected_u0
    if not math.isclose(replay0_own, nc.br0.value, rel_tol=1e-10, abs_tol=1e-10):
        raise RuntimeError(f"{name}: P0 BR direct/replay mismatch")
    if not math.isclose(replay1_own, nc.br1.value, rel_tol=1e-10, abs_tol=1e-10):
        raise RuntimeError(f"{name}: P1 BR direct/replay mismatch")

    # In a zero-sum game the unilateral gain against a self-play profile is
    # BR0-u0 for P0 and BR1+u0 for P1; their sum is NashConv.
    p0_gain = nc.br0.value - self_play.expected_u0
    p1_gain = nc.br1.value + self_play.expected_u0
    if p0_gain < -1e-9 or p1_gain < -1e-9:
        raise RuntimeError(
            f"{name}: best-response gain became negative: p0={p0_gain} p1={p1_gain}"
        )
    if not math.isclose(p0_gain + p1_gain, nc.nash_conv, rel_tol=1e-10, abs_tol=1e-10):
        raise RuntimeError(f"{name}: unilateral gains do not sum to NashConv")

    return {
        "profile_sha256": _profile_sha256(profile),
        "self_play_expected_u0": self_play.expected_u0,
        "self_play_terminal_leaves": self_play.terminal_leaves,
        "self_play_information_states_seen": self_play.information_states_seen,
        "br0": {
            "own_value": nc.br0.value,
            "gain_over_self_play": max(0.0, p0_gain),
            "round3_infosets": nc.br0.round3_infosets,
            "round4_infosets": nc.br0.round4_infosets,
            "choice_count": len(nc.br0.choices),
            "terminal_leaves": nc.br0.terminal_leaves,
            "independent_replay_u0": replay0.expected_u0,
        },
        "br1": {
            "own_value": nc.br1.value,
            "gain_over_self_play": max(0.0, p1_gain),
            "round3_infosets": nc.br1.round3_infosets,
            "round4_infosets": nc.br1.round4_infosets,
            "choice_count": len(nc.br1.choices),
            "terminal_leaves": nc.br1.terminal_leaves,
            "independent_replay_u0": replay1.expected_u0,
        },
        "nash_conv": nc.nash_conv,
        "exploitability": nc.exploitability,
        "authority": AUTHORITY,
    }


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
    mccfr_snapshot = trainer.snapshot()

    support = build_reachable_infoset_support(state, worlds)
    max_actions = max(len(row.action_keys) for row in support)
    resolve_iterations = max(RESOLVE_MIN_ITERATIONS, max_actions)

    search_completed = complete_profile_with_counterfactual_resolve(
        search_base,
        support,
        iterations_per_infoset=resolve_iterations,
        seed=SEARCH_RESOLVE_SEED,
        exploration=1.0,
    )
    mccfr_completed = complete_profile_with_counterfactual_resolve(
        mccfr_base,
        support,
        iterations_per_infoset=resolve_iterations,
        seed=MCCFR_RESOLVE_SEED,
        exploration=1.0,
    )
    if search_completed.completed_information_states != len(support):
        raise RuntimeError("05E search completion did not cover full reachable support")
    if mccfr_completed.completed_information_states != len(support):
        raise RuntimeError("05E MCCFR completion did not cover full reachable support")

    search_result = _evaluate_algorithm(
        state,
        worlds,
        support,
        name="search",
        profile=search_completed.profile,
    )
    mccfr_result = _evaluate_algorithm(
        state,
        worlds,
        support,
        name="mccfr",
        profile=mccfr_completed.profile,
    )

    delta_exploitability = search_result["exploitability"] - mccfr_result["exploitability"]
    preferred = (
        "MCCFR"
        if delta_exploitability > 1e-12
        else "SEARCH"
        if delta_exploitability < -1e-12
        else "TIE_WITHIN_1E12"
    )

    source_paths = [
        "tools/openofc_solver/external_two_street_infoset_search.py",
        "tools/openofc_solver/external_two_street_mccfr.py",
        "tools/openofc_solver/external_two_street_counterfactual_resolve.py",
        "tools/openofc_solver/external_two_street_exact_br.py",
        "tools/openofc_solver/test_external_two_street_exact_br.py",
        "tools/openofc_solver/run_external_two_street_05e.py",
        "tools/openofc_solver/EXTERNAL_TWO_STREET_05E_EXACT_BR_CONTRACT.md",
        "tools/openofc_solver/strategic_cfr.py",
    ]
    payload = {
        "schema": "openofc-external-component-ab-v1",
        "experiment_id": EXPERIMENT_ID,
        "authority": AUTHORITY,
        "component": "exact-reduced-game-nashconv-search-vs-mccfr",
        "fixed_game": {
            "support_worlds": len(worlds),
            "reachable_information_states": len(support),
            "p0_information_states": sum(1 for row in support if row.actor == 0),
            "p1_information_states": sum(1 for row in support if row.actor == 1),
            "max_legal_actions": max_actions,
            "uniform_physical_world_chance": True,
            "canonical_terminal_utility": True,
            "canonical_infoset_keys": True,
        },
        "provenance": {
            "q1_run_id": Q1_RUN_ID,
            "q1_manifest_sha256": Q1_MANIFEST_SHA256,
            "search_iterations": UCT_ITERATIONS,
            "search_seed": UCT_SEED,
            "mccfr_iterations": MCCFR_ITERATIONS,
            "mccfr_seed": MCCFR_SEED,
            "completion_iterations_per_missing_infoset": resolve_iterations,
            "search_completion_seed": SEARCH_RESOLVE_SEED,
            "mccfr_completion_seed": MCCFR_RESOLVE_SEED,
            "search_base_information_states": len(search_base),
            "mccfr_base_information_states": mccfr_snapshot.information_states,
            "search_completed_information_states": search_completed.completed_information_states,
            "mccfr_completed_information_states": mccfr_completed.completed_information_states,
        },
        "search": search_result,
        "mccfr": mccfr_result,
        "comparison": {
            "search_minus_mccfr_exploitability": delta_exploitability,
            "lower_exploitability_on_this_reduced_game": preferred,
            "head_to_head_signal_from_q1_mccfr_p0_vs_search_p1": 27.70528074597922,
            "head_to_head_signal_is_not_used_to_compute_nashconv": True,
        },
        "quality": {
            "search_nashconv_finite_nonnegative": math.isfinite(search_result["nash_conv"]) and search_result["nash_conv"] >= 0.0,
            "mccfr_nashconv_finite_nonnegative": math.isfinite(mccfr_result["nash_conv"]) and mccfr_result["nash_conv"] >= 0.0,
            "search_br_replays_match_direct": True,
            "mccfr_br_replays_match_direct": True,
            "search_profile_complete": search_completed.completed_information_states == len(support),
            "mccfr_profile_complete": mccfr_completed.completed_information_states == len(support),
            "no_unseen_infoset_fallback": True,
            "no_full_game_equilibrium_claim": True,
            "no_real_route_certification_claim": True,
        },
        "files": [
            {"path": path, "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}
            for path in source_paths
        ],
        "limitations": [
            "exact only on the frozen six-world R3-R4 reduced game",
            "profiles are Q1-completed local policies rather than full earlier-round posterior-conditioned strategies",
            "Q1 completion uses uniform compatible-state search prior",
            "MCCFR profile is current regret matching rather than a separately validated reach-weighted CFR average",
            "no Fantasy continuation or Bellman continuation value is included",
            "no transfer theorem from reduced-game exploitability to the full OpenOFC game",
        ],
        "promotion_recommendation": "USE_05E_WITH_05D_Q2_TO_SELECT_NEXT_REDUCED_GAME_ARCHITECTURE_EXPERIMENT_ONLY",
        "real_routes_certified": 0,
    }
    if not all(payload["quality"].values()):
        raise RuntimeError(f"05E exact reduced-game gate failed: {payload['quality']}")
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    payload["sha256"] = hashlib.sha256(raw).hexdigest()
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/external_two_street_05e.json")
    args = parser.parse_args()
    payload = run()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "experiment_id": payload["experiment_id"],
        "search": {
            "self_play_u0": payload["search"]["self_play_expected_u0"],
            "br0": payload["search"]["br0"]["own_value"],
            "br1": payload["search"]["br1"]["own_value"],
            "nash_conv": payload["search"]["nash_conv"],
            "exploitability": payload["search"]["exploitability"],
        },
        "mccfr": {
            "self_play_u0": payload["mccfr"]["self_play_expected_u0"],
            "br0": payload["mccfr"]["br0"]["own_value"],
            "br1": payload["mccfr"]["br1"]["own_value"],
            "nash_conv": payload["mccfr"]["nash_conv"],
            "exploitability": payload["mccfr"]["exploitability"],
        },
        "lower_exploitability": payload["comparison"]["lower_exploitability_on_this_reduced_game"],
        "manifest_sha256": payload["sha256"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
