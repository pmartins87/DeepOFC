from __future__ import annotations

"""Run the exact reduced-game Appendix-C M-star optimistic floor pilot."""

import hashlib
import json
from pathlib import Path

from deepofc.hu_two_round_br import exact_nash_conv
from deepofc.hu_two_round_cfr import TwoRoundFullTreeCFR
from deepofc.hu_two_round_hidden_discard import HUTwoRoundHiddenDiscardSubgame
from deepofc.hu_two_round_joker import HUTwoRoundJokerSubgame
from m5p_external_sampling_theoretical_bound import project_raw_pairwise_utility_range
from m5q_variance_mstar_floor import appendix_c_mstar_zero_variance_floor

SCHEMA = "openofc-m5q-appendix-c-mstar-floor-pilot-v1"
AUTHORITY = "APPENDIX_C_MSTAR_VARIANCE_FLOOR_PILOT_NOT_CERTIFICATION"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "m5q_variance_mstar_floor.json"
TARGET = 0.15
PROBE_ITERATIONS = 1_000_000
SAMPLING_FLOOR = 1.0
RAW_RANGE = project_raw_pairwise_utility_range()


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _source_manifest() -> dict[str, object]:
    paths = (
        "deepofc/hu_two_round.py",
        "deepofc/hu_two_round_br.py",
        "deepofc/hu_two_round_cfr.py",
        "deepofc/hu_two_round_hidden_discard.py",
        "deepofc/hu_two_round_joker.py",
        "tools/openofc_solver/M5Q_VARIANCE_MSTAR_FLOOR_CONTRACT.md",
        "tools/openofc_solver/m5p_external_sampling_theoretical_bound.py",
        "tools/openofc_solver/m5q_variance_mstar_floor.py",
        "tools/openofc_solver/run_m5q_variance_mstar_floor.py",
        "tools/openofc_solver/test_m5q_variance_mstar_floor.py",
    )
    rows = [
        {"path": rel, "sha256": hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()}
        for rel in paths
    ]
    payload: dict[str, object] = {"files": rows}
    payload["sha256"] = _sha(payload)
    return payload


def _profile_rows(family_id: str, game, profiles: list[tuple[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for profile_id, profile in profiles:
        exact, br0, br1 = exact_nash_conv(game, profile)
        surfaces: dict[str, object] = {}
        for label, utility_range in (("unit", 1.0), ("project_raw", RAW_RANGE)):
            floor = appendix_c_mstar_zero_variance_floor(
                game,
                profile,
                utility_range=utility_range,
                sampling_probability_floor=SAMPLING_FLOOR,
            )
            surfaces[label] = {
                "floor": floor.payload(),
                "bound_at_probe_iterations": floor.bound_at(PROBE_ITERATIONS),
                "required_iterations_for_target": floor.required_iterations(TARGET),
            }
        rows.append(
            {
                "family_id": family_id,
                "profile_id": profile_id,
                "exact_nash_conv": exact,
                "exact_exploitability": 0.5 * exact,
                "br0_value": br0.value,
                "br1_value": br1.value,
                "surfaces": surfaces,
                "production_certification_eligible": False,
            }
        )
    return rows


def main() -> None:
    joker = HUTwoRoundJokerSubgame()
    joker_solver = TwoRoundFullTreeCFR(joker, variant="cfr")
    joker_solver.run(8)

    hidden = HUTwoRoundHiddenDiscardSubgame()
    hidden_solver = TwoRoundFullTreeCFR(hidden, variant="cfr")
    hidden_solver.run(1)

    rows: list[dict[str, object]] = []
    rows.extend(
        _profile_rows(
            "joker",
            joker,
            [
                ("uniform", joker.uniform_profile()),
                ("standard-cfr-average-8", joker_solver.average_profile()),
            ],
        )
    )
    rows.extend(
        _profile_rows(
            "hidden-discard",
            hidden,
            [
                ("uniform", hidden.uniform_profile()),
                ("standard-cfr-average-1", hidden_solver.average_profile()),
            ],
        )
    )

    unit_required = [
        int(row["surfaces"]["unit"]["required_iterations_for_target"])
        for row in rows
    ]
    raw_required = [
        int(row["surfaces"]["project_raw"]["required_iterations_for_target"])
        for row in rows
    ]
    mstar_ratios = []
    for row in rows:
        floor = row["surfaces"]["unit"]["floor"]
        for player_key in ("player0", "player1"):
            player = floor[player_key]
            mstar_ratios.append(
                float(player["best_response_m_value"]) / float(player["static_m_value"])
            )

    payload: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "theorem_source": "Gibson long-form Appendix C Theorem C.1",
        "target_exploitability": TARGET,
        "probe_iterations": PROBE_ITERATIONS,
        "sampling_probability_floor_assumption": SAMPLING_FLOOR,
        "variance_assumption": 0.0,
        "utility_ranges": {"unit": 1.0, "project_raw": RAW_RANGE},
        "source_manifest": _source_manifest(),
        "rows": rows,
        "summary": {
            "rows": len(rows),
            "min_best_response_m_to_static_ratio": min(mstar_ratios),
            "max_best_response_m_to_static_ratio": max(mstar_ratios),
            "min_unit_required_iterations_for_0_15": min(unit_required),
            "max_unit_required_iterations_for_0_15": max(unit_required),
            "min_raw_required_iterations_for_0_15": min(raw_required),
            "max_raw_required_iterations_for_0_15": max(raw_required),
            "actual_variance_measured": False,
            "actual_sampling_floor_measured": False,
            "production_certification_eligible": False,
            "real_routes_certified": 0,
        },
    }
    payload["sha256"] = _sha(payload)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"artifact": str(OUT.relative_to(ROOT)), "sha256": payload["sha256"], "summary": payload["summary"]}, sort_keys=True))


if __name__ == "__main__":
    main()
