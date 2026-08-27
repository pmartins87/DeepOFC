from __future__ import annotations

"""Run a reproducible two-state M5B->M5I->M5H Normal/Normal screening pilot.

This driver intentionally produces HELD_OUT_SCREENING_ONLY evidence.  It is a
pipeline/calibration experiment, not a certification run and not an M4Z route
promotion attempt.
"""

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from typing import Sequence

from hu_continuation import HUContinuationState, KERNEL_NORMAL_NORMAL, zero_continuation_values
from m5b_adaptive_normal_oracles import AdaptiveNormalConfig, AdaptiveNormalNormalOracle
from m5c_route_certification import EVIDENCE_SCREENING
from m5h_normal_heldout_evidence import collect_normal_route_evidence
from m5h_reference_evaluator_manifest import (
    CAPABILITY_SCREENING_ONLY,
    METHOD_LEARNED_RESPONSE_LOWER_BOUND,
    freeze_reference_evaluator_manifest,
)
from m5i_normal_normal_screening import (
    AUTHORITY as M5I_AUTHORITY,
    HeldoutSeedSpec,
    NormalNormalScreeningConfig,
    screen_normal_normal_candidate,
)

SCHEMA = "openofc-m5i-normal-normal-two-state-pilot-v1"
AUTHORITY = "SCREENING_PILOT_NOT_CERTIFICATION"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "m5i_normal_normal_pilot.json"

CANDIDATE_CONFIG = AdaptiveNormalConfig(
    training_iterations=256,
    evaluation_samples=64,
    replay_capacity=20_000,
    fit_epochs=2,
    model_buckets=1 << 12,
    learning_rate=0.08,
    l2=1e-6,
    huber_delta=1.0,
    epsilon=0.6,
    base_seed=2026082701,
)
SCREEN_CONFIG = NormalNormalScreeningConfig(
    response_training_iterations=256,
    heldout_samples_per_seed=64,
    epsilon=0.6,
    base_seed=2026082702,
)
HELDOUT_SEEDS = (
    HeldoutSeedSpec("m5i-pilot-heldout-01:2026082711", 2026082711),
    HeldoutSeedSpec("m5i-pilot-heldout-02:2026082729", 2026082729),
    HeldoutSeedSpec("m5i-pilot-heldout-03:2026082747", 2026082747),
    HeldoutSeedSpec("m5i-pilot-heldout-04:2026082763", 2026082763),
)


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_manifest(paths: Sequence[str]) -> dict[str, object]:
    rows = []
    for rel in sorted(paths):
        path = ROOT / rel
        rows.append({"path": rel, "sha256": _file_sha(path)})
    payload: dict[str, object] = {"files": rows}
    payload["sha256"] = _sha(payload)
    return payload


def _candidate_sources() -> dict[str, object]:
    return _source_manifest(
        (
            "tools/openofc_solver/m5a_normal_normal_oracle.py",
            "tools/openofc_solver/m5b_adaptive_normal_oracles.py",
            "tools/openofc_solver/strategic_advantage_model.py",
            "tools/openofc_solver/strategic_continuation_cfr.py",
            "tools/openofc_solver/strategic_policy_distillation.py",
            "tools/openofc_solver/strategic_suit_symmetry.py",
        )
    )


def _screen_sources() -> dict[str, object]:
    return _source_manifest(
        (
            "tools/openofc_solver/m5i_normal_normal_screening.py",
            "tools/openofc_solver/strategic_cfr.py",
            "tools/openofc_solver/strategic_suit_symmetry.py",
        )
    )


def _screen_validation_sources() -> dict[str, object]:
    return _source_manifest(
        (
            "tools/openofc_solver/M5I_NORMAL_NORMAL_SCREENING_CONTRACT.md",
            "tools/openofc_solver/test_m5i_normal_normal_screening.py",
            "tools/openofc_solver/test_m5b_adaptive_normal_oracles.py",
            ".github/workflows/openofc-m5h-normal-heldout-evidence.yml",
        )
    )


def main() -> None:
    continuation_values = zero_continuation_values()
    candidate_sources = _candidate_sources()
    screen_sources = _screen_sources()
    validation_sources = _screen_validation_sources()
    reference = freeze_reference_evaluator_manifest(
        evaluator_id="m5i-normal-normal-learned-response-screen-v1",
        implementation_sha256=str(screen_sources["sha256"]),
        validation_evidence_sha256=str(validation_sources["sha256"]),
        method_class=METHOD_LEARNED_RESPONSE_LOWER_BOUND,
        capability=CAPABILITY_SCREENING_ONLY,
        validated_kernel_kinds=(KERNEL_NORMAL_NORMAL,),
        reference_authority=M5I_AUTHORITY,
        validation_provenance=(
            "M5I screening implementation contract/tests; this evidence validates "
            "screening mechanics only and carries no low-exploitability authority"
        ),
    )

    route_rows: list[dict[str, object]] = []
    for button in (0, 1):
        state = HUContinuationState(button, 0, 0)
        adaptive = AdaptiveNormalNormalOracle(CANDIDATE_CONFIG)
        materialized = adaptive.materialize_fixed_policy(
            state, continuation_values
        )
        screen = screen_normal_normal_candidate(
            materialized.fixed_oracle,
            state,
            continuation_values,
            HELDOUT_SEEDS,
            SCREEN_CONFIG,
            provenance=(
                f"M5I pilot state={state.as_key()} "
                f"candidate_materialization={materialized.report.sha256}"
            ),
        )
        response_training_ids = tuple(
            row.training_seed_id for row in screen.response_training
        )
        all_training_ids = (
            materialized.report.training_seed_ids + response_training_ids
        )
        bundle = collect_normal_route_evidence(
            materialized.fixed_oracle,
            state,
            continuation_values,
            screen.seed_metrics,
            implementation_sha256=str(candidate_sources["sha256"]),
            reference_evaluator=reference,
            training_seed_ids=all_training_ids,
            provenance=(
                f"M5B materialization={materialized.report.sha256} | "
                f"M5I screening={screen.sha256} | pilot={SCHEMA}"
            ),
            evidence_kind=EVIDENCE_SCREENING,
        )
        route_rows.append(
            {
                "state": state.as_key(),
                "materialization": asdict(materialized.report),
                "screening": asdict(screen),
                "m5h_report": asdict(bundle.report),
                "m5c_evidence": asdict(bundle.route_evidence),
                "promotion_allowed": False,
                "promotion_block_reason": (
                    "HELD_OUT_SCREENING_ONLY is non-certifying by M5C contract"
                ),
            }
        )

    payload: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "candidate_config": CANDIDATE_CONFIG.payload(),
        "screen_config": SCREEN_CONFIG.payload(),
        "heldout_seeds": [asdict(seed) for seed in HELDOUT_SEEDS],
        "candidate_source_manifest": candidate_sources,
        "screen_source_manifest": screen_sources,
        "screen_validation_source_manifest": validation_sources,
        "reference_evaluator_manifest": asdict(reference),
        "routes": route_rows,
        "summary": {
            "routes_screened": len(route_rows),
            "states": [row["state"] for row in route_rows],
            "max_observed_deviation_gain": max(
                float(row["screening"]["max_observed_deviation_gain"])  # type: ignore[index]
                for row in route_rows
            ),
            "ready_for_real_bellman": 0,
            "certification_claimed": False,
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
                **payload["summary"],  # type: ignore[arg-type]
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
