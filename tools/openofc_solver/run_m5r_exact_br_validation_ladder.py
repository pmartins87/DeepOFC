from __future__ import annotations

"""Authoritative M5R-B exact best-response validation-ladder cell runner.

This runner is deliberately certification-ineligible.  It validates the exact
reference BR construction on the two frozen three-round reduced games required
by ``M5R_EXACT_BR_VALIDATION_LADDER_CONTRACT.md``.  The scalable/full-game
challenger remains a separate M5R problem.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
from time import perf_counter
from typing import Any

from deepofc.hu_three_round_br import exact_best_response, exact_value_of_pure_response
from deepofc.hu_three_round_sequential import HUThreeRoundSequentialSubgame
from deepofc.hu_three_round_sequential_v2 import HUThreeRoundSequentialSubgameV2


SCHEMA = "openofc-m5r-exact-br-validation-ladder-cell-v1"
AUTHORITY = "REFERENCE_EVALUATOR_VALIDATION_ONLY_NOT_ROUTE_CERTIFICATION"
TOLERANCE = 1e-10

FAMILIES: dict[str, dict[str, Any]] = {
    "three-round-v1": {
        "factory": HUThreeRoundSequentialSubgame,
        "game_name": "HUThreeRoundSequentialSubgame",
        "game_source": "deepofc/hu_three_round_sequential.py",
        "expected_exact_terminal_histories": 1_312_200,
        "expected_pure_replay_terminal_histories": 3_240,
    },
    "three-round-v2": {
        "factory": HUThreeRoundSequentialSubgameV2,
        "game_name": "HUThreeRoundSequentialSubgameV2",
        "game_source": "deepofc/hu_three_round_sequential_v2.py",
        "expected_exact_terminal_histories": 839_808,
        "expected_pure_replay_terminal_histories": 5_184,
    },
}


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _response_fingerprint(response: Any) -> str:
    lines = sorted(
        f"{repr(info)}\t{repr(action.key())}"
        for info, action in response.choices.items()
    )
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def _decoy_zero_mass_responder_profile(game: Any, response: Any) -> tuple[dict, int, int]:
    """Put zero mass on responder alternatives without changing opponent uniformity.

    The exact BR must ignore the responder's supplied behavioral probabilities.
    Re-running against this decoy therefore directly proves that responder
    alternatives carrying zero supplied mass are still enumerated.
    """

    profile: dict = {}
    zero_mass_actions = 0
    total_legal_actions = 0
    for info in response.choices:
        legal = game.actions(info)
        if not legal:
            raise AssertionError("responding-player infoset has no legal actions")
        profile[info] = {
            action: 1.0 if index == 0 else 0.0
            for index, action in enumerate(legal)
        }
        total_legal_actions += len(legal)
        zero_mass_actions += max(0, len(legal) - 1)
    if zero_mass_actions <= 0:
        raise AssertionError("validation cell did not expose a zero-mass responder alternative")
    return profile, zero_mass_actions, total_legal_actions


def run_cell(family: str, player: int) -> dict[str, Any]:
    if family not in FAMILIES:
        raise ValueError(f"family must be one of {tuple(FAMILIES)}")
    if player not in (0, 1):
        raise ValueError("player must be 0 or 1")

    spec = FAMILIES[family]
    game = spec["factory"]()
    uniform_profile: dict = {}

    started = perf_counter()
    response = exact_best_response(game, uniform_profile, player)
    exact_seconds = perf_counter() - started

    expected_exact = int(spec["expected_exact_terminal_histories"])
    if response.terminal_histories != expected_exact:
        raise AssertionError(
            f"{family} P{player} exact work drift: "
            f"{response.terminal_histories} != {expected_exact}"
        )
    if not response.choices:
        raise AssertionError("exact BR returned no responding-player infosets")

    illegal_choices = 0
    for info, chosen in response.choices.items():
        if chosen not in game.actions(info):
            illegal_choices += 1
    if illegal_choices:
        raise AssertionError(f"exact BR selected {illegal_choices} illegal actions")

    started = perf_counter()
    replay_value, replay_histories = exact_value_of_pure_response(
        game, uniform_profile, response
    )
    replay_seconds = perf_counter() - started
    expected_replay = int(spec["expected_pure_replay_terminal_histories"])
    if replay_histories != expected_replay:
        raise AssertionError(
            f"{family} P{player} replay work drift: "
            f"{replay_histories} != {expected_replay}"
        )

    value_error = abs(float(response.value) - float(replay_value))
    if not math.isfinite(value_error) or value_error > TOLERANCE:
        raise AssertionError(
            f"{family} P{player} exact/replay disagreement: {value_error} > {TOLERANCE}"
        )

    primary_fingerprint = _response_fingerprint(response)
    decoy_profile, zero_mass_actions, total_legal_actions = (
        _decoy_zero_mass_responder_profile(game, response)
    )

    started = perf_counter()
    zero_mass_response = exact_best_response(game, decoy_profile, player)
    zero_mass_seconds = perf_counter() - started
    if zero_mass_response.terminal_histories != expected_exact:
        raise AssertionError("zero-mass responder diagnostic changed exact work")
    if abs(float(zero_mass_response.value) - float(response.value)) > TOLERANCE:
        raise AssertionError("responder supplied probabilities leaked into exact BR value")
    zero_mass_fingerprint = _response_fingerprint(zero_mass_response)
    if zero_mass_fingerprint != primary_fingerprint:
        raise AssertionError("responder zero-mass decoy changed deterministic pure BR choices")

    repo_root = Path(__file__).resolve().parents[2]
    source_paths = {
        "contract": repo_root / "tools/openofc_solver/M5R_EXACT_BR_VALIDATION_LADDER_CONTRACT.md",
        "exact_br": repo_root / "deepofc/hu_three_round_br.py",
        "game": repo_root / str(spec["game_source"]),
        "runner": Path(__file__).resolve(),
    }
    source_sha256 = {name: _sha256_file(path) for name, path in source_paths.items()}

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "family": family,
        "game": str(spec["game_name"]),
        "responding_player": player,
        "frozen_profile": {
            "semantics": "EMPTY_PROFILE_USES_GAME_DEFINED_UNIFORM_FALLBACK",
            "opponent_behavior": "UNIFORM_OVER_EVERY_LEGAL_ACTION",
            "responding_player_behavior": "IGNORED_BY_EXACT_BR",
        },
        "contract": {
            "tolerance": TOLERANCE,
            "expected_exact_terminal_histories": expected_exact,
            "expected_pure_replay_terminal_histories": expected_replay,
        },
        "exact_best_response": {
            "value": float(response.value),
            "responding_player_infosets": len(response.choices),
            "responding_player_legal_actions_across_infosets": total_legal_actions,
            "terminal_histories": int(response.terminal_histories),
            "pure_response_sha256": primary_fingerprint,
            "seconds": exact_seconds,
        },
        "independent_state_apply_replay": {
            "value": float(replay_value),
            "terminal_histories": int(replay_histories),
            "absolute_value_error": value_error,
            "seconds": replay_seconds,
        },
        "zero_mass_responder_alternative_guard": {
            "supplied_zero_mass_legal_actions": zero_mass_actions,
            "exact_terminal_histories": int(zero_mass_response.terminal_histories),
            "value": float(zero_mass_response.value),
            "pure_response_sha256": zero_mass_fingerprint,
            "seconds": zero_mass_seconds,
            "all_zero_mass_alternatives_still_enumerated": True,
            "responder_probabilities_do_not_affect_br": True,
        },
        "source_sha256": source_sha256,
        "decision": {
            "exact_work_count_matches_contract": True,
            "pure_replay_work_count_matches_contract": True,
            "exact_and_independent_replay_agree": True,
            "responding_player_infoset_coverage_guard_passed": True,
            "all_selected_actions_legal": True,
            "zero_mass_responder_alternatives_enumerated": True,
            "production_certification_eligible": False,
            "real_routes_certified": 0,
        },
        "verdict": "PASS_M5R_EXACT_BR_VALIDATION_LADDER_CELL",
        "production_certification_eligible": False,
        "real_routes_certified": 0,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode(
        "utf-8"
    )
    payload["manifest_sha256"] = hashlib.sha256(raw).hexdigest()
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--family", required=True, choices=tuple(FAMILIES))
    parser.add_argument("--player", required=True, type=int, choices=(0, 1))
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    payload = run_cell(args.family, args.player)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "family": payload["family"],
                "responding_player": payload["responding_player"],
                "exact_best_response": payload["exact_best_response"],
                "independent_state_apply_replay": payload["independent_state_apply_replay"],
                "zero_mass_responder_alternative_guard": payload[
                    "zero_mass_responder_alternative_guard"
                ],
                "verdict": payload["verdict"],
                "manifest_sha256": payload["manifest_sha256"],
                "real_routes_certified": 0,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
