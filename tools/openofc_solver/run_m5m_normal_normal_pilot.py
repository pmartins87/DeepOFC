from __future__ import annotations

"""Run a reproducible two-state M5B -> M5M -> M5H screening pilot.

M5M replaces the exact-key held-out response fallback used by M5I with a
visible-information generalized response and evaluates candidate/response
profiles on paired deals and policy-uniform streams.  The resulting evidence is
still a learned-response lower bound and therefore remains screening-only.
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
from m5i_normal_normal_screening import HeldoutSeedSpec
from m5m_generalized_response_screening import (
    AUTHORITY as M5M_AUTHORITY,
    GeneralizedResponseConfig,
    screen_generalized_normal_normal_candidate,
)

SCHEMA = "openofc-m5m-normal-normal-two-state-pilot-v1"
AUTHORITY = "GENERALIZED_PAIRED_RESPONSE_PILOT_NOT_CERTIFICATION"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "m5m_normal_normal_pilot.json"

CANDIDATE_CONFIG = AdaptiveNormalConfig(
    training_iterations=1024,
    evaluation_samples=128,
    replay_capacity=50_000,
    fit_epochs=2,
    model_buckets=1 << 13,
    learning_rate=0.08,
    l2=1e-6,
    huber_delta=1.0,
    epsilon=0.6,
    base_seed=2026082701,
)
SCREEN_CONFIG = GeneralizedResponseConfig(
    response_training_iterations=1024,
    epsilon=0.6,
    replay_capacity=80_000,
    fit_epochs=2,
    model_buckets=1 << 13,
    learning_rate=0.08,
    l2=1e-6,
    huber_delta=1.0,
    heldout_samples_per_seed=256,
    confidence_multiplier=3.182,
    base_seed=2026082941,
)
HELDOUT_SEEDS = (
    HeldoutSeedSpec("m5m-pilot-heldout-01:2026082711", 2026082711),
    HeldoutSeedSpec("m5m-pilot-heldout-02:2026082729", 2026082729),
    HeldoutSeedSpec("m5m-pilot-heldout-03:2026082747", 2026082747),
    HeldoutSeedSpec("m5m-pilot-heldout-04:2026082763", 2026082763),
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
            "tools/openofc_solver/m5m_generalized_response_screening.py",
            "tools/openofc_solver/strategic_advantage_model.py",
            "tools/openofc_solver/strategic_policy_distillation.py",
            "tools/openofc_solver/strategic_cfr.py",
            "tools/openofc_solver/strategic_suit_symmetry.py",
        )
    )


def _validation_sources() -> dict[str, object]:
    return _source_manifest(
        (
            "tools/openofc_solver/M5M_GENERALIZED_RESPONSE_SCREENING_CONTRACT.md",
            "tools/openofc_solver/test_m5m_generalized_response_screening.py",
            ".github/workflows/openofc-m5m-generalized-response.yml",
        )
    )


def main() -> None:
    continuation_values = zero_continuation_values()
    candidate_sources = _candidate_sources()
    screen_sources = _screen_sources()
    validation_sources = _validation_sources()
    reference = freeze_reference_evaluator_manifest(
        evaluator_id="m5m-generalized-paired-response-screen-v1",
        implementation_sha256=str(screen_sources["sha256"]),
        validation_evidence_sha256=str(validation_sources["sha256"]),
        method_class=METHOD_LEARNED_RESPONSE_LOWER_BOUND,
        capability=CAPABILITY_SCREENING_ONLY,
        validated_kernel_kinds=(KERNEL_NORMAL_NORMAL,),
        reference_authority=M5M_AUTHORITY,
        validation_provenance=(
            "M5M contract/tests validate generalized visible-information response, "
            "paired rollout mechanics and uncertainty accounting only. They do not "
            "establish a low-exploitability upper bound."
        ),
    )

    route_rows: list[dict[str, object]] = []
    for button in (0, 1):
        state = HUContinuationState(button, 0, 0)
        adaptive = AdaptiveNormalNormalOracle(CANDIDATE_CONFIG)
        materialized = adaptive.materialize_fixed_policy(state, continuation_values)
        screen = screen_generalized_normal_normal_candidate(
            materialized.fixed_oracle,
            state,
            continuation_values,
            HELDOUT_SEEDS,
            SCREEN_CONFIG,
            provenance=(
                f"M5M pilot state={state.as_key()} "
                f"candidate_materialization={materialized.report.sha256}"
            ),
        )

        response_training_ids: list[str] = []
        for report in screen.response_materializations:
            response_training_ids.extend(
                (report.training_seed_id, report.replay_seed_id, report.model_seed_id)
            )
        all_training_ids = (
            materialized.report.training_seed_ids + tuple(response_training_ids)
        )
        bundle = collect_normal_route_evidence(
            materialized.fixed_oracle,
            state,
            continuation_values,
            tuple(metric.as_m5h_diagnostic() for metric in screen.paired_seed_metrics),
            implementation_sha256=str(candidate_sources["sha256"]),
            reference_evaluator=reference,
            training_seed_ids=all_training_ids,
            provenance=(
                f"M5B materialization={materialized.report.sha256} | "
                f"M5M screening={screen.sha256} | pilot={SCHEMA}"
            ),
            evidence_kind=EVIDENCE_SCREENING,
        )
        route_rows.append(
            {
                "state": state.as_key(),
                "candidate_materialization": asdict(materialized.report),
                "m5m_screening": asdict(screen),
                "m5h_report": asdict(bundle.report),
                "m5c_evidence": asdict(bundle.route_evidence),
                "promotion_allowed": False,
                "promotion_block_reason": (
                    "M5M learned-response lower bound is HELD_OUT_SCREENING_ONLY"
                ),
            }
        )

    payload: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "continuation_vector": "ZERO",
        "candidate_config": CANDIDATE_CONFIG.payload(),
        "screen_config": SCREEN_CONFIG.payload(),
        "heldout_seeds": [asdict(seed) for seed in HELDOUT_SEEDS],
        "candidate_source_manifest": candidate_sources,
        "screen_source_manifest": screen_sources,
        "validation_source_manifest": validation_sources,
        "reference_evaluator_manifest": asdict(reference),
        "routes": route_rows,
        "summary": {
            "routes_screened": len(route_rows),
            "states": [row["state"] for row in route_rows],
            "max_conservative_deviation_signal": max(
                float(row["m5m_screening"]["max_conservative_deviation_signal"])  # type: ignore[index]
                for row in route_rows
            ),
            "max_seed_mean_signed_gain": max(
                max(
                    float(row["m5m_screening"]["p0_aggregate"]["seed_mean_signed_gain"]),  # type: ignore[index]
                    float(row["m5m_screening"]["p1_aggregate"]["seed_mean_signed_gain"]),  # type: ignore[index]
                )
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
