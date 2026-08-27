from __future__ import annotations

"""Run the frozen M5Q sampled-regret unbiasedness implementation diagnostic."""

import hashlib
import json
from pathlib import Path

from deepofc.hu_two_round_joker import HUTwoRoundJokerSubgame
from m5q_external_sampling_unbiasedness import (
    AUTHORITY as DIAGNOSTIC_AUTHORITY,
    run_projection_unbiasedness_diagnostic,
)

SCHEMA = "openofc-m5q-sampled-regret-unbiasedness-pilot-v1"
AUTHORITY = "EXTERNAL_SAMPLING_UNBIASEDNESS_PILOT_NOT_CERTIFICATION"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "m5q_external_sampling_unbiasedness.json"
PROBES = 4096
PROJECTION_COUNT = 8
STANDARD_ERROR_MULTIPLIER = 6.0
PROFILE_RUNS = (
    ("uniform", 2026090101),
    ("hash-mixed", 2026090137),
)


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _source_manifest() -> dict[str, object]:
    paths = (
        "deepofc/hu_two_round.py",
        "deepofc/hu_two_round_cfr.py",
        "deepofc/hu_two_round_joker.py",
        "deepofc/hu_two_round_mccfr.py",
        "tools/openofc_solver/M5Q_EXTERNAL_SAMPLING_UNBIASEDNESS_CONTRACT.md",
        "tools/openofc_solver/m5q_external_sampling_unbiasedness.py",
        "tools/openofc_solver/run_m5q_external_sampling_unbiasedness.py",
        "tools/openofc_solver/test_m5q_external_sampling_unbiasedness.py",
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


def main() -> None:
    game = HUTwoRoundJokerSubgame()
    rows = []
    for profile_rule, seed in PROFILE_RUNS:
        diagnostic = run_projection_unbiasedness_diagnostic(
            game,
            profile_rule=profile_rule,
            probes=PROBES,
            rng_seed=seed,
            projection_count=PROJECTION_COUNT,
            standard_error_multiplier=STANDARD_ERROR_MULTIPLIER,
        )
        rows.append(diagnostic.payload())

    payload: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "diagnostic_authority": DIAGNOSTIC_AUTHORITY,
        "game_family": "joker",
        "probes_per_profile": PROBES,
        "projection_count": PROJECTION_COUNT,
        "standard_error_multiplier": STANDARD_ERROR_MULTIPLIER,
        "profile_runs": [
            {"profile_rule": profile_rule, "rng_seed": seed}
            for profile_rule, seed in PROFILE_RUNS
        ],
        "source_manifest": _source_manifest(),
        "rows": rows,
        "summary": {
            "profiles": [row["profile_rule"] for row in rows],
            "all_profile_probability_surfaces_equal": all(
                float(row["profile_max_probability_difference"]) <= 1e-15
                for row in rows
            ),
            "all_projections_pass": all(bool(row["all_projections_pass"]) for row in rows),
            "max_standardized_error": max(
                float(row["max_standardized_error"]) for row in rows
            ),
            "max_absolute_error": max(float(row["max_absolute_error"]) for row in rows),
            "certification_eligible": False,
            "concentration_certificate_emitted": False,
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
    if not payload["summary"]["all_profile_probability_surfaces_equal"]:
        raise SystemExit("M5Q frozen strategy surfaces differ")
    if not payload["summary"]["all_projections_pass"]:
        raise SystemExit("M5Q sampled regret unbiasedness diagnostic failed")


if __name__ == "__main__":
    main()
