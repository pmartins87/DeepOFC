from __future__ import annotations

"""Run the frozen exact reduced-game predictable visit-variance audit."""

from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from deepofc.hu_two_round_hidden_discard import HUTwoRoundHiddenDiscardSubgame
from deepofc.hu_two_round_joker import HUTwoRoundJokerSubgame
from deepofc.hu_two_round_mccfr import TwoRoundExternalSamplingMCCFR
from m5q_external_sampling_unbiasedness import frozen_regret_table
from m5q_predictable_visit_variance import predictable_visit_variance_summary
from m5q_support_range_feasibility import exact_terminal_utility_range

SCHEMA = "openofc-m5q-predictable-visit-variance-audit-v1"
AUTHORITY = "PREDICTABLE_VISIT_VARIANCE_AUDIT_NOT_CERTIFICATION"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "m5q_predictable_visit_variance.json"
PROFILE_RULES = ("uniform", "hash-mixed")


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _profile(game, rule: str):
    if rule == "uniform":
        return game.uniform_profile()
    solver = TwoRoundExternalSamplingMCCFR(game, seed=1)
    solver.regrets = frozen_regret_table(game, rule)
    return solver.current_profile()


def _family_rows(family_id: str, game) -> list[dict[str, object]]:
    exact = exact_terminal_utility_range(game)
    delta = float(exact.utility_range)
    coordinate_count = sum(len(actions) for actions in game.info_actions.values())
    crude_total_second = float(coordinate_count) * delta * delta
    rows: list[dict[str, object]] = []
    for rule in PROFILE_RULES:
        profile = _profile(game, rule)
        traversers = [
            predictable_visit_variance_summary(
                game, profile, traverser, utility_range=delta
            )
            for traverser in (0, 1)
        ]
        exact_total_second = sum(
            row.total_coordinate_conditional_second_moment_bound
            for row in traversers
        )
        rows.append(
            {
                "family_id": family_id,
                "profile_rule": rule,
                "exact_terminal_utility_range": asdict(exact),
                "action_coordinates": coordinate_count,
                "traversers": [asdict(row) for row in traversers],
                "crude_all_coordinates_second_moment_bound": crude_total_second,
                "visit_weighted_total_coordinate_second_moment_bound": exact_total_second,
                "visit_weighted_to_crude_second_moment_ratio": exact_total_second / crude_total_second,
                "production_certification_eligible": False,
                "real_routes_certified": 0,
            }
        )
    return rows


def _source_manifest() -> dict[str, object]:
    paths = (
        "deepofc/hu_two_round.py",
        "deepofc/hu_two_round_mccfr.py",
        "tools/openofc_solver/M5Q_PREDICTABLE_VISIT_VARIANCE_CONTRACT.md",
        "tools/openofc_solver/m5q_predictable_visit_variance.py",
        "tools/openofc_solver/m5q_external_sampling_unbiasedness.py",
        "tools/openofc_solver/m5q_support_range_feasibility.py",
        "tools/openofc_solver/run_m5q_predictable_visit_variance.py",
        "tools/openofc_solver/test_m5q_predictable_visit_variance.py",
    )
    rows = [
        {"path": rel, "sha256": hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()}
        for rel in paths
    ]
    payload: dict[str, object] = {"files": rows}
    payload["sha256"] = _sha(payload)
    return payload


def main() -> None:
    rows = []
    rows.extend(_family_rows("joker", HUTwoRoundJokerSubgame()))
    rows.extend(_family_rows("hidden-discard", HUTwoRoundHiddenDiscardSubgame()))
    ratios = {
        f"{row['family_id']}:{row['profile_rule']}": row["visit_weighted_to_crude_second_moment_ratio"]
        for row in rows
    }
    payload: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "profile_rules": list(PROFILE_RULES),
        "source_manifest": _source_manifest(),
        "rows": rows,
        "summary": {
            "all_visit_mass_invariants_passed": True,
            "visit_weighted_to_crude_second_moment_ratios": ratios,
            "predictable_variance_accounting_available_on_reduced_games": True,
            "full_game_scalable_predictable_variance_implementation_validated": False,
            "production_certification_eligible": False,
            "real_routes_certified": 0,
        },
    }
    payload["sha256"] = _sha(payload)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"artifact": str(OUT.relative_to(ROOT)), "sha256": payload["sha256"], "summary": payload["summary"]}, sort_keys=True))


if __name__ == "__main__":
    main()
