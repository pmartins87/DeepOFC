from __future__ import annotations

"""Run a reproducible two-route M5B->M5K->M5H Normal/Fantasy screening pilot.

This is deliberately screening-only.  It compares a frozen 256-iteration M5B
candidate with an independently trained 1024-iteration challenger at the exact
same continuation vector and evaluates both on paired held-out physical deals.
Nothing emitted here is certification eligible or may promote an M4Z route.
"""

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from typing import Sequence

from hu_continuation import (
    HUContinuationState,
    KERNEL_NORMAL_FANTASY,
    zero_continuation_values,
)
from m5b_adaptive_normal_oracles import AdaptiveNormalConfig, AdaptiveNormalFantasyOracle
from m5c_route_certification import EVIDENCE_SCREENING
from m5h_normal_heldout_evidence import collect_normal_route_evidence
from m5h_reference_evaluator_manifest import (
    CAPABILITY_SCREENING_ONLY,
    METHOD_LEARNED_RESPONSE_LOWER_BOUND,
    freeze_reference_evaluator_manifest,
)
from m5k_normal_fantasy_screening import (
    AUTHORITY as M5K_AUTHORITY,
    HeldoutSeedSpec,
    NormalFantasyScreeningConfig,
    screen_normal_fantasy_candidate,
)
from normal_fantasy_terminal import ExactOnePassNormalFantasyTerminalEvaluator

SCHEMA = "openofc-m5k-normal-fantasy-two-route-pilot-v1"
AUTHORITY = "NORMAL_FANTASY_SCREENING_PILOT_NOT_CERTIFICATION"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "m5k_normal_fantasy_pilot.json"

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
    base_seed=2026082811,
)
CHALLENGER_CONFIG = AdaptiveNormalConfig(
    training_iterations=1024,
    evaluation_samples=64,
    replay_capacity=80_000,
    fit_epochs=2,
    model_buckets=1 << 13,
    learning_rate=0.08,
    l2=1e-6,
    huber_delta=1.0,
    epsilon=0.6,
    base_seed=2026082837,
)
SCREEN_CONFIG = NormalFantasyScreeningConfig(
    heldout_samples_per_seed=64,
    base_seed=2026082861,
)
HELDOUT_SEEDS = (
    HeldoutSeedSpec("m5k-pilot-heldout-01:2026082873", 2026082873),
    HeldoutSeedSpec("m5k-pilot-heldout-02:2026082889", 2026082889),
    HeldoutSeedSpec("m5k-pilot-heldout-03:2026082907", 2026082907),
    HeldoutSeedSpec("m5k-pilot-heldout-04:2026082921", 2026082921),
)
ROUTES = (
    HUContinuationState(0, 0, 14),
    HUContinuationState(1, 17, 0),
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
        rows.append({"path": rel, "sha256": _file_sha(ROOT / rel)})
    payload: dict[str, object] = {"files": rows}
    payload["sha256"] = _sha(payload)
    return payload


def _candidate_sources() -> dict[str, object]:
    return _source_manifest(
        (
            "tools/openofc_solver/m5a_normal_fantasy_oracle.py",
            "tools/openofc_solver/m5b_adaptive_normal_oracles.py",
            "tools/openofc_solver/normal_fantasy_cfr.py",
            "tools/openofc_solver/normal_fantasy_policy_distillation.py",
            "tools/openofc_solver/normal_fantasy_terminal.py",
            "tools/openofc_solver/strategic_advantage_model.py",
        )
    )


def _screen_sources() -> dict[str, object]:
    return _source_manifest(
        (
            "tools/openofc_solver/m5k_normal_fantasy_screening.py",
            "tools/openofc_solver/normal_fantasy_kernel.py",
            "tools/openofc_solver/normal_fantasy_symmetry.py",
            "tools/openofc_solver/run_m5k_normal_fantasy_pilot.py",
        )
    )


def _validation_sources() -> dict[str, object]:
    return _source_manifest(
        (
            "tools/openofc_solver/M5K_NORMAL_FANTASY_SCREENING_CONTRACT.md",
            "tools/openofc_solver/test_m5k_normal_fantasy_screening.py",
            ".github/workflows/openofc-m5k-normal-fantasy-screening.yml",
            ".github/workflows/openofc-m5k-normal-fantasy-pilot.yml",
        )
    )


def main() -> None:
    continuation_values = zero_continuation_values()
    candidate_sources = _candidate_sources()
    screen_sources = _screen_sources()
    validation_sources = _validation_sources()
    reference = freeze_reference_evaluator_manifest(
        evaluator_id="m5k-normal-fantasy-independent-challenger-screen-v1",
        implementation_sha256=str(screen_sources["sha256"]),
        validation_evidence_sha256=str(validation_sources["sha256"]),
        method_class=METHOD_LEARNED_RESPONSE_LOWER_BOUND,
        capability=CAPABILITY_SCREENING_ONLY,
        validated_kernel_kinds=(KERNEL_NORMAL_FANTASY,),
        reference_authority=M5K_AUTHORITY,
        validation_provenance=(
            "M5K contract/tests plus paired held-out challenger implementation; "
            "screening mechanics only, with no exploitability upper-bound authority"
        ),
    )

    route_rows: list[dict[str, object]] = []
    for state in ROUTES:
        terminal = ExactOnePassNormalFantasyTerminalEvaluator()
        candidate_adaptive = AdaptiveNormalFantasyOracle(
            CANDIDATE_CONFIG,
            terminal_evaluator=terminal,
            terminal_evaluator_id=terminal.authority,
        )
        challenger_adaptive = AdaptiveNormalFantasyOracle(
            CHALLENGER_CONFIG,
            terminal_evaluator=terminal,
            terminal_evaluator_id=terminal.authority,
        )
        candidate = candidate_adaptive.materialize_fixed_policy(
            state, continuation_values
        )
        challenger = challenger_adaptive.materialize_fixed_policy(
            state, continuation_values
        )

        candidate_training = set(candidate.report.training_seed_ids)
        challenger_training = set(challenger.report.training_seed_ids)
        if candidate_training & challenger_training:
            raise RuntimeError("M5K candidate/challenger training seed identities overlap")

        screen = screen_normal_fantasy_candidate(
            candidate.fixed_oracle,
            challenger.fixed_oracle,
            state,
            continuation_values,
            HELDOUT_SEEDS,
            SCREEN_CONFIG,
            terminal_evaluator=terminal,
            terminal_evaluator_id=terminal.authority,
            provenance=(
                f"M5K pilot state={state.as_key()} | "
                f"candidate={candidate.report.sha256} | "
                f"challenger={challenger.report.sha256}"
            ),
        )
        training_ids = tuple(
            sorted(candidate_training | challenger_training)
        )
        bundle = collect_normal_route_evidence(
            candidate.fixed_oracle,
            state,
            continuation_values,
            screen.seed_metrics,
            implementation_sha256=str(candidate_sources["sha256"]),
            reference_evaluator=reference,
            training_seed_ids=training_ids,
            provenance=(
                f"M5B candidate={candidate.report.sha256} | "
                f"M5B challenger={challenger.report.sha256} | "
                f"M5K screening={screen.sha256} | pilot={SCHEMA}"
            ),
            evidence_kind=EVIDENCE_SCREENING,
        )
        route_rows.append(
            {
                "state": state.as_key(),
                "candidate_materialization": asdict(candidate.report),
                "challenger_materialization": asdict(challenger.report),
                "screening": asdict(screen),
                "m5h_report": asdict(bundle.report),
                "m5c_evidence": asdict(bundle.route_evidence),
                "terminal_evaluator": {
                    "authority": terminal.authority,
                    "evaluations": terminal.evaluations,
                    "exact_cache_hits": terminal.exact_hits,
                    "exact_cache_misses": terminal.exact_misses,
                },
                "promotion_allowed": False,
                "promotion_block_reason": (
                    "HELD_OUT_SCREENING_ONLY is non-certifying by M5C contract"
                ),
            }
        )

    payload: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "continuation_regime": "ZERO_VECTOR_CURRENT_HAND_ONLY_PILOT",
        "candidate_config": CANDIDATE_CONFIG.payload(),
        "challenger_config": CHALLENGER_CONFIG.payload(),
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
            "max_observed_deviation_gain": max(
                float(row["screening"]["max_observed_deviation_gain"])
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
                **payload["summary"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
