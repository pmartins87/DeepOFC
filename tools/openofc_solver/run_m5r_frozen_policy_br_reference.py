from __future__ import annotations

"""Run the frozen M5R exact reduced-game best-response reference gate."""

import hashlib
import json
from pathlib import Path

from deepofc.hu_two_round_hidden_discard import HUTwoRoundHiddenDiscardSubgame
from deepofc.hu_two_round_joker import HUTwoRoundJokerSubgame
from m5r_frozen_policy_br_reference import (
    REFERENCE_AUTHORITY,
    freeze_reference_evaluator_manifest,
    validate_exact_reference,
)

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "m5r_frozen_policy_br_reference.json"


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _file_sha(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def _source_manifest() -> dict[str, object]:
    paths = (
        "deepofc/hu_two_round.py",
        "deepofc/hu_two_round_br.py",
        "deepofc/hu_two_round_joker.py",
        "deepofc/hu_two_round_hidden_discard.py",
        "tools/openofc_solver/M5R_FROZEN_POLICY_BR_CERTIFICATION_CONTRACT.md",
        "tools/openofc_solver/m5r_frozen_policy_br_reference.py",
        "tools/openofc_solver/run_m5r_frozen_policy_br_reference.py",
        "tools/openofc_solver/test_m5r_frozen_policy_br_reference.py",
    )
    rows = [{"path": rel, "sha256": _file_sha(rel)} for rel in paths]
    payload: dict[str, object] = {"files": rows}
    payload["sha256"] = _sha(payload)
    return payload


def main() -> None:
    joker = HUTwoRoundJokerSubgame()
    hidden = HUTwoRoundHiddenDiscardSubgame()
    validation = validate_exact_reference(
        (
            ("joker", joker, joker.uniform_profile()),
            ("hidden-discard", hidden, hidden.uniform_profile()),
        )
    )
    implementation_sha = _file_sha(
        "tools/openofc_solver/m5r_frozen_policy_br_reference.py"
    )
    manifest = freeze_reference_evaluator_manifest(
        evaluator_id="m5r-exact-two-round-reference-v1",
        implementation_sha256=implementation_sha,
        validation_evidence_sha256=validation.sha256,
        validation_status=validation.validation_status,
        validation_scope=validation.validation_scope,
        evaluator_authority=REFERENCE_AUTHORITY,
        guaranteed_missed_deviation_upper_bound=0.0,
        certification_eligible=True,
        provenance="M5R exact reduced-game reference validation",
    )

    payload: dict[str, object] = {
        "validation": validation.payload(),
        "reference_evaluator_manifest": manifest.payload(),
        "source_manifest": _source_manifest(),
        "decision": {
            "reduced_game_reference_architecture_validated": (
                validation.validation_status == "PASS"
                and manifest.certification_eligible
                and manifest.guaranteed_missed_deviation_upper_bound == 0.0
            ),
            "full_game_scalable_evaluator_validated": False,
            "m5b_candidate_promoted": False,
            "production_route_certification_eligible": False,
            "real_routes_certified": 0,
            "next_blocker": "SCALABLE_EVALUATOR_WITH_INDEPENDENT_MISSED_DEVIATION_UPPER_BOUND_MISSING",
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
                "validation_sha256": validation.sha256,
                "manifest_sha256": manifest.sha256,
                "rows": {
                    row.family_id: {
                        "profile_sha256": row.profile_sha256,
                        "exploitability": row.exploitability,
                        "max_unilateral_deviation_gain": row.max_unilateral_deviation_gain,
                        "crosscheck_max_abs_error": row.independent_value_crosscheck_max_abs_error,
                    }
                    for row in validation.rows
                },
                "next_blocker": payload["decision"]["next_blocker"],
                "real_routes_certified": 0,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
