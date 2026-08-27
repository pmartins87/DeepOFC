from __future__ import annotations

"""Quantify the impossible-best-case floor of Gibson et al. Theorem 2."""

import hashlib
import json
from pathlib import Path

from deepofc.hu_two_round_hidden_discard import HUTwoRoundHiddenDiscardSubgame
from deepofc.hu_two_round_joker import HUTwoRoundJokerSubgame
from m5q_variance_theorem_floor import zero_variance_theorem_floor

SCHEMA = "openofc-m5q-variance-theorem-floor-pilot-v1"
AUTHORITY = "GIBSON_THEOREM2_OPTIMISTIC_FLOOR_PILOT_NOT_CERTIFICATION"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "m5q_variance_theorem_floor.json"
TARGETS = (1.0, 0.25, 0.15, 0.05)
DELTA_HATS = (1.0, 206.0)
PROBE_ITERATIONS = 1_000_000


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _source_manifest() -> dict[str, object]:
    paths = (
        "deepofc/hu_two_round.py",
        "deepofc/hu_two_round_hidden_discard.py",
        "deepofc/hu_two_round_joker.py",
        "tools/openofc_solver/M5Q_VARIANCE_THEOREM_FLOOR_CONTRACT.md",
        "tools/openofc_solver/m5q_variance_theorem_floor.py",
        "tools/openofc_solver/run_m5q_variance_theorem_floor.py",
        "tools/openofc_solver/test_m5q_variance_theorem_floor.py",
    )
    rows = [
        {
            "path": rel,
            "sha256": hashlib.sha256((ROOT / rel).read_bytes()).hexdigest(),
        }
        for rel in paths
    ]
    payload: dict[str, object] = {"files": rows}
    payload["sha256"] = _sha(payload)
    return payload


def _family_row(family_id: str, game) -> dict[str, object]:
    surfaces: dict[str, object] = {}
    for delta_hat in DELTA_HATS:
        label = "unit" if delta_hat == 1.0 else "project_raw_206"
        floor = zero_variance_theorem_floor(game, delta_hat=delta_hat)
        surfaces[label] = {
            "floor": floor.payload(),
            "probe_iterations": PROBE_ITERATIONS,
            "probe_exploitability_upper_bound": floor.bound_at(PROBE_ITERATIONS),
            "required_iterations": {
                str(target): floor.required_iterations(target) for target in TARGETS
            },
        }
    return {
        "family_id": family_id,
        "variance_assumption": 0.0,
        "surfaces": surfaces,
        "production_certification_eligible": False,
    }


def main() -> None:
    rows = [
        _family_row("joker", HUTwoRoundJokerSubgame()),
        _family_row("hidden-discard", HUTwoRoundHiddenDiscardSubgame()),
    ]
    payload: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "variance_assumption": 0.0,
        "targets": list(TARGETS),
        "delta_hats": list(DELTA_HATS),
        "probe_iterations": PROBE_ITERATIONS,
        "source_manifest": _source_manifest(),
        "rows": rows,
        "summary": {
            "families": [row["family_id"] for row in rows],
            "rows": len(rows),
            "min_unit_iterations_for_0_15": min(
                int(row["surfaces"]["unit"]["required_iterations"]["0.15"])
                for row in rows
            ),
            "max_unit_iterations_for_0_15": max(
                int(row["surfaces"]["unit"]["required_iterations"]["0.15"])
                for row in rows
            ),
            "max_raw_206_iterations_for_0_15": max(
                int(row["surfaces"]["project_raw_206"]["required_iterations"]["0.15"])
                for row in rows
            ),
            "variance_measurement_needed_for_rejection": False,
            "certification_eligible": False,
            "real_routes_certified": 0,
        },
    }
    payload["sha256"] = _sha(payload)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "artifact": str(OUT.relative_to(ROOT)),
                "sha256": payload["sha256"],
                "summary": payload["summary"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
