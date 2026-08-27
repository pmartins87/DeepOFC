from __future__ import annotations

"""M5J diagnostic ladder for the two Normal/Normal routes.

The ladder asks a narrow question before the project scales held-out work to the
remaining route families: do stronger M5B candidate training budgets reduce the
learned-response lower bound, and does a stronger M5I response recover the
apparent weakness?

Every row remains HELD_OUT_SCREENING_ONLY.  No threshold is selected here and
no result can promote a route into REAL Bellman authority.
"""

from dataclasses import asdict
import hashlib
import json
from pathlib import Path

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

SCHEMA = "openofc-m5j-normal-normal-budget-ladder-v1"
AUTHORITY = "BUDGET_LADDER_DIAGNOSTIC_NOT_CERTIFICATION"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "m5j_normal_normal_budget_ladder.json"

CANDIDATE_BUDGETS = (256, 1024)
RESPONSE_BUDGETS = (256, 1024)
HELDOUT_SAMPLES_PER_SEED = 128
HELDOUT_SEEDS = (
    HeldoutSeedSpec("m5j-heldout-01:2026082711", 2026082711),
    HeldoutSeedSpec("m5j-heldout-02:2026082729", 2026082729),
    HeldoutSeedSpec("m5j-heldout-03:2026082747", 2026082747),
    HeldoutSeedSpec("m5j-heldout-04:2026082763", 2026082763),
)
CANDIDATE_BASE_SEED = 2026082701
RESPONSE_BASE_SEED = 2026082702


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_manifest(paths: tuple[str, ...]) -> dict[str, object]:
    rows = [
        {"path": rel, "sha256": _file_sha(ROOT / rel)}
        for rel in sorted(paths)
    ]
    payload: dict[str, object] = {"files": rows}
    payload["sha256"] = _sha(payload)
    return payload


def _candidate_config(iterations: int) -> AdaptiveNormalConfig:
    return AdaptiveNormalConfig(
        training_iterations=iterations,
        evaluation_samples=128,
        replay_capacity=50_000,
        fit_epochs=2,
        model_buckets=1 << 13,
        learning_rate=0.08,
        l2=1e-6,
        huber_delta=1.0,
        epsilon=0.6,
        base_seed=CANDIDATE_BASE_SEED,
    )


def _screen_config(iterations: int) -> NormalNormalScreeningConfig:
    return NormalNormalScreeningConfig(
        response_training_iterations=iterations,
        heldout_samples_per_seed=HELDOUT_SAMPLES_PER_SEED,
        epsilon=0.6,
        base_seed=RESPONSE_BASE_SEED,
    )


def main() -> None:
    continuation_values = zero_continuation_values()
    candidate_sources = _source_manifest(
        (
            "tools/openofc_solver/m5a_normal_normal_oracle.py",
            "tools/openofc_solver/m5b_adaptive_normal_oracles.py",
            "tools/openofc_solver/strategic_advantage_model.py",
            "tools/openofc_solver/strategic_continuation_cfr.py",
            "tools/openofc_solver/strategic_policy_distillation.py",
            "tools/openofc_solver/strategic_suit_symmetry.py",
        )
    )
    screen_sources = _source_manifest(
        (
            "tools/openofc_solver/m5i_normal_normal_screening.py",
            "tools/openofc_solver/strategic_cfr.py",
            "tools/openofc_solver/strategic_suit_symmetry.py",
        )
    )
    validation_sources = _source_manifest(
        (
            "tools/openofc_solver/M5I_NORMAL_NORMAL_SCREENING_CONTRACT.md",
            "tools/openofc_solver/test_m5i_normal_normal_screening.py",
            "tools/openofc_solver/test_m5b_adaptive_normal_oracles.py",
            ".github/workflows/openofc-m5h-normal-heldout-evidence.yml",
        )
    )
    reference = freeze_reference_evaluator_manifest(
        evaluator_id="m5j-normal-normal-learned-response-budget-ladder-v1",
        implementation_sha256=str(screen_sources["sha256"]),
        validation_evidence_sha256=str(validation_sources["sha256"]),
        method_class=METHOD_LEARNED_RESPONSE_LOWER_BOUND,
        capability=CAPABILITY_SCREENING_ONLY,
        validated_kernel_kinds=(KERNEL_NORMAL_NORMAL,),
        reference_authority=M5I_AUTHORITY,
        validation_provenance=(
            "M5I screening contract/tests. M5J reuses it only as a screening "
            "lower-bound diagnostic across deterministic budget levels."
        ),
    )

    rows: list[dict[str, object]] = []
    for button in (0, 1):
        state = HUContinuationState(button, 0, 0)
        for candidate_budget in CANDIDATE_BUDGETS:
            candidate_config = _candidate_config(candidate_budget)
            adaptive = AdaptiveNormalNormalOracle(candidate_config)
            materialized = adaptive.materialize_fixed_policy(
                state, continuation_values
            )
            for response_budget in RESPONSE_BUDGETS:
                screen_config = _screen_config(response_budget)
                screen = screen_normal_normal_candidate(
                    materialized.fixed_oracle,
                    state,
                    continuation_values,
                    HELDOUT_SEEDS,
                    screen_config,
                    provenance=(
                        f"M5J state={state.as_key()} candidate_budget={candidate_budget} "
                        f"response_budget={response_budget} "
                        f"candidate={materialized.report.sha256}"
                    ),
                )
                response_training_ids = tuple(
                    report.training_seed_id for report in screen.response_training
                )
                bundle = collect_normal_route_evidence(
                    materialized.fixed_oracle,
                    state,
                    continuation_values,
                    screen.seed_metrics,
                    implementation_sha256=str(candidate_sources["sha256"]),
                    reference_evaluator=reference,
                    training_seed_ids=(
                        materialized.report.training_seed_ids
                        + response_training_ids
                    ),
                    provenance=(
                        f"M5J budget ladder candidate={materialized.report.sha256} "
                        f"screen={screen.sha256}"
                    ),
                    evidence_kind=EVIDENCE_SCREENING,
                )
                rows.append(
                    {
                        "state": state.as_key(),
                        "candidate_budget": candidate_budget,
                        "response_budget": response_budget,
                        "candidate_config_sha256": candidate_config.sha256,
                        "screen_config_sha256": screen_config.sha256,
                        "materialization": asdict(materialized.report),
                        "screening": asdict(screen),
                        "m5h_report": asdict(bundle.report),
                        "m5c_evidence": asdict(bundle.route_evidence),
                        "promotion_allowed": False,
                    }
                )

    compact = [
        {
            "state": row["state"],
            "candidate_budget": row["candidate_budget"],
            "response_budget": row["response_budget"],
            "max_unilateral_deviation": row["m5h_report"]["max_unilateral_deviation"],  # type: ignore[index]
            "value_standard_error": row["m5h_report"]["value_standard_error"],  # type: ignore[index]
        }
        for row in rows
    ]

    payload: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "continuation_vector": "ZERO",
        "candidate_budgets": list(CANDIDATE_BUDGETS),
        "response_budgets": list(RESPONSE_BUDGETS),
        "heldout_samples_per_seed": HELDOUT_SAMPLES_PER_SEED,
        "heldout_seeds": [asdict(seed) for seed in HELDOUT_SEEDS],
        "candidate_source_manifest": candidate_sources,
        "screen_source_manifest": screen_sources,
        "validation_source_manifest": validation_sources,
        "reference_evaluator_manifest": asdict(reference),
        "rows": rows,
        "compact": compact,
        "summary": {
            "states": ["B0:P0F0:P1F0", "B1:P0F0:P1F0"],
            "rows": len(rows),
            "ready_for_real_bellman": 0,
            "certification_claimed": False,
            "max_observed_deviation_gain": max(
                float(row["max_unilateral_deviation"]) for row in compact
            ),
        },
    }
    payload["sha256"] = _sha(payload)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"artifact": str(OUT.relative_to(ROOT)), "sha256": payload["sha256"], "compact": compact}, sort_keys=True))


if __name__ == "__main__":
    main()
