from __future__ import annotations

"""Run the first exact reduced-game M5O regret-bound pilot.

The pilot validates implementation/theorem agreement and measures practical bound
tightness. It does not certify any production route and does not transfer the
result to MCCFR.
"""

import hashlib
import json
from pathlib import Path

from deepofc.hu_two_round_cfr import TwoRoundFullTreeCFR
from deepofc.hu_two_round_hidden_discard import HUTwoRoundHiddenDiscardSubgame
from deepofc.hu_two_round_joker import HUTwoRoundJokerSubgame
from m5o_regret_certificate import certify_two_round_standard_cfr

SCHEMA = "openofc-m5o-regret-certificate-pilot-v1"
AUTHORITY = "REDUCED_GAME_REGRET_BOUND_PILOT_NOT_PRODUCTION_CERTIFICATION"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "m5o_regret_certificate_pilot.json"

# Frozen before observing pilot results. Joker is the cheaper multi-checkpoint
# convergence surface; hidden-discard is a materially larger transfer check.
FAMILY_CHECKPOINTS = {
    "joker": (1, 2, 4, 8),
    "hidden-discard": (1,),
}


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
        "tools/openofc_solver/M5O_REGRET_CERTIFICATE_FEASIBILITY_CONTRACT.md",
        "tools/openofc_solver/m5o_regret_certificate.py",
        "tools/openofc_solver/run_m5o_regret_certificate_pilot.py",
        "tools/openofc_solver/test_m5o_regret_certificate.py",
    )
    rows = []
    for rel in paths:
        rows.append(
            {
                "path": rel,
                "sha256": hashlib.sha256((ROOT / rel).read_bytes()).hexdigest(),
            }
        )
    payload: dict[str, object] = {"files": rows}
    payload["sha256"] = _sha(payload)
    return payload


def _run_family(family_id: str, game, checkpoints: tuple[int, ...]) -> list[dict[str, object]]:
    solver = TwoRoundFullTreeCFR(game, variant="cfr")
    rows: list[dict[str, object]] = []
    previous = 0
    for target in checkpoints:
        if target <= previous:
            raise ValueError("M5O checkpoints must be strictly increasing")
        solver.run(target - previous)
        certificate = certify_two_round_standard_cfr(solver)
        exact = certificate.exact_nash_conv
        bound = certificate.nash_conv_upper_bound
        rows.append(
            {
                "family_id": family_id,
                "checkpoint": target,
                "certificate": certificate.payload(),
                "bound_to_exact_nash_conv_ratio": (
                    None if exact <= 0.0 else bound / exact
                ),
                "production_certification_eligible": False,
            }
        )
        previous = target
    return rows


def main() -> None:
    rows: list[dict[str, object]] = []
    rows.extend(
        _run_family(
            "joker",
            HUTwoRoundJokerSubgame(),
            FAMILY_CHECKPOINTS["joker"],
        )
    )
    rows.extend(
        _run_family(
            "hidden-discard",
            HUTwoRoundHiddenDiscardSubgame(),
            FAMILY_CHECKPOINTS["hidden-discard"],
        )
    )

    slacks = [float(row["certificate"]["nash_conv_bound_slack"]) for row in rows]
    ratios = [
        float(row["bound_to_exact_nash_conv_ratio"])
        for row in rows
        if row["bound_to_exact_nash_conv_ratio"] is not None
    ]
    payload: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "solver_variant": "cfr",
        "family_checkpoints": {
            key: list(value) for key, value in FAMILY_CHECKPOINTS.items()
        },
        "source_manifest": _source_manifest(),
        "rows": rows,
        "summary": {
            "rows": len(rows),
            "families": sorted({str(row["family_id"]) for row in rows}),
            "all_bounds_verified": all(
                bool(row["certificate"]["bound_verified"]) for row in rows
            ),
            "min_bound_slack": min(slacks),
            "max_bound_slack": max(slacks),
            "min_bound_to_exact_ratio": min(ratios) if ratios else None,
            "max_bound_to_exact_ratio": max(ratios) if ratios else None,
            "production_certification_eligible": False,
            "mccfr_transfer_claimed": False,
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
